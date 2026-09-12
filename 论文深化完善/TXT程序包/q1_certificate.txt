"""问题1可复现求解。运行 python solve_q1.py，依赖 numpy scipy openpyxl matplotlib。"""
from pathlib import Path
import sys, json, csv, hashlib
HERE = Path(__file__).resolve().parent
if (HERE / 'pydeps').exists():
    sys.path.insert(0, str(HERE / 'pydeps'))
import numpy as np
import scipy
from scipy.optimize import linprog
import openpyxl

ROOT = HERE.parent
OUT = HERE.parent / '计算结果'
OUT.mkdir(exist_ok=True)

def solve(price, load, pv, eta=.9, power=5000., initial=6000., cyclic=True, method='highs-ds'):
    # x = [grid(144), charge(144), discharge(144), spill(144), energy(145)]
    n = len(price); nv = 5*n+1; dt = 1/6
    A = np.zeros((2*n, nv)); b = np.zeros(2*n)
    for t in range(n):
        A[t,[t,n+t,2*n+t,3*n+t]] = [1,-1,1,-1]
        b[t] = (load[t]-pv[t])*dt
        A[n+t,[n+t,2*n+t,4*n+t,4*n+t+1]] = [-eta,1/eta,-1,1]
    bounds = ([(0,None)]*n+[(0,power*dt)]*(2*n)
              +[(0,float(v*dt)) for v in pv]+[(1200,10800)]*(n+1))
    bounds[4*n]=(initial,initial)
    if cyclic: bounds[-1]=(initial,initial)
    c=np.r_[price,np.zeros(4*n+1)]
    r=linprog(c,A_eq=A,b_eq=b,bounds=bounds,method=method)
    if not r.success: raise RuntimeError(r.message)
    x=r.x; q,ch,dis,spill=np.split(x[:4*n],4); e=x[4*n:]
    dual=float(b@r.eqlin.marginals)
    for j,(lo,hi) in enumerate(bounds):
        if lo is not None: dual+=lo*r.lower.marginals[j]
        if hi is not None: dual+=hi*r.upper.marginals[j]
    balance=q+pv*dt+dis-load*dt-ch-spill
    dyn=np.diff(e)-eta*ch+dis/eta
    checks={'balance_max_abs_kwh':float(np.max(np.abs(balance))),
            'storage_max_abs_kwh':float(np.max(np.abs(dyn))),
            'initial_kwh':float(e[0]),'terminal_kwh':float(e[-1]),
            'minimum_storage_kwh':float(e.min()),'maximum_storage_kwh':float(e.max()),
            'maximum_charge_kw':float(ch.max()/dt),'maximum_discharge_kw':float(dis.max()/dt),
            'simultaneous_charge_discharge_slots':int(np.sum((ch>1e-7)&(dis>1e-7))),
            'dual_objective_yuan':dual,'primal_dual_gap_yuan':float(abs(r.fun-dual)),
            'global_energy_residual_kwh':float(q.sum()+pv.sum()*dt-load.sum()*dt-spill.sum()-(1-eta)*ch.sum()-(1/eta-1)*dis.sum()-(e[-1]-e[0]))}
    return {'cost':float(r.fun),'purchase':float(q.sum()),'charge':float(ch.sum()),
            'discharge':float(dis.sum()),'spill':float(spill.sum()),'q':q.tolist(),
            'c':ch.tolist(),'d':dis.tolist(),'w':spill.tolist(),'e':e.tolist(),'checks':checks}

def main():
    p=ROOT/'input'/'附件1.xlsx'
    ws=openpyxl.load_workbook(p,data_only=True).active
    rows=list(ws.values)[1:]
    assert len(rows)==144
    a=np.array([r[1:] for r in rows],dtype=float)
    price,load,pv=a.T
    assert np.isfinite(a).all() and (a>=0).all()
    def minute(v):
        if hasattr(v,'hour'): return v.hour*60+v.minute
        return 1440 if '+1' in v else int(v.split(':')[0])*60+int(v.split(':')[1])
    assert [minute(r[0]) for r in rows]==list(range(10,1441,10))
    res=solve(price,load,pv)
    baseline=np.maximum(load-pv,0)/6
    res.update({'load_total':float(load.sum()/6),'pv_total':float(pv.sum()/6),
                'baseline_cost':float(price@baseline),'baseline_purchase':float(baseline.sum()),
                'baseline_spill':float(np.maximum(pv-load,0).sum()/6),
                'price_min':float(price.min()),'price_max':float(price.max()),
                'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                'scipy_version':scipy.__version__,'numpy_version':np.__version__,
                'price':price.tolist(),'load':load.tolist(),'pv':pv.tolist()})
    res['savings']=res['baseline_cost']-res['cost']
    res['savings_pct']=100*res['savings']/res['baseline_cost']
    res['blocks']=[{'period':f'{i*4}:00-{(i+1)*4}:00',
                   'charge':sum(res['c'][i*24:(i+1)*24]),
                   'discharge':sum(res['d'][i*24:(i+1)*24])} for i in range(6)]
    res['selected']=[{'period':f'{h}:00-{h}:10','q':res['q'][h*6]} for h in [10,12,14,16,18,20]]
    sensitivity=[]
    for label,eta,power,initial,cyclic in [
        ('充放电各85%',.85,5000,6000,True),('充放电各90%',.9,5000,6000,True),
        ('往返效率90%',np.sqrt(.9),5000,6000,True),('最大功率4000kW',.9,4000,6000,True),
        ('最大功率6000kW',.9,6000,6000,True),('初始电量1200kWh',.9,5000,1200,True),
        ('初始电量10800kWh',.9,5000,10800,True),('不约束日末回归',.9,5000,6000,False)]:
        z=solve(price,load,pv,eta,power,initial,cyclic)
        sensitivity.append({'case':label,'cost':z['cost'],'purchase':z['purchase'],'end':z['e'][-1]})
    shifted=solve(np.roll(price,1),np.roll(load,1),np.roll(pv,1))
    sensitivity.append({'case':'时刻作区间起点并循环补0时','cost':shifted['cost'],'purchase':shifted['purchase'],'end':shifted['e'][-1]})
    res['sensitivity']=sensitivity
    alt=solve(price,load,pv,method='highs-ipm')
    res['checks']['independent_algorithm_cost_gap_yuan']=abs(alt['cost']-res['cost'])
    assert res['checks']['balance_max_abs_kwh']<1e-6
    assert res['checks']['storage_max_abs_kwh']<1e-6
    assert res['checks']['primal_dual_gap_yuan']<1e-5
    assert res['checks']['simultaneous_charge_discharge_slots']==0
    assert abs(res['e'][-1]-6000)<1e-6
    (OUT/'summary.json').write_text(json.dumps(res,ensure_ascii=False,indent=2),encoding='utf-8')
    def tm(m): return f'{m//60:02d}:{m%60:02d}'
    with (OUT/'逐时段策略.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['序号','时间段','电价元每kWh','负载kW','光伏kW','购电kWh','充电kWh','放电kWh','弃光kWh','段初SOC_kWh','段末SOC_kWh','购电费元'])
        for t in range(144):w.writerow([t+1,tm(10*t)+'-'+tm(10*(t+1)),price[t],load[t],pv[t],res['q'][t],res['c'][t],res['d'][t],res['w'][t],res['e'][t],res['e'][t+1],price[t]*res['q'][t]])
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.sans-serif':['Microsoft YaHei'],'axes.unicode_minus':False,'font.size':10})
    t=np.arange(144)/6
    fig,axs=plt.subplots(3,1,figsize=(9,7),sharex=True,constrained_layout=True)
    axs[0].step(t,load,where='post',label='小区负载',color='#283747')
    axs[0].step(t,pv,where='post',label='光伏预测功率',color='#da8b00')
    axs[0].step(t,np.array(res['q'])*6,where='post',label='计划购电功率',color='#2874a6',alpha=.85)
    axs[0].set_ylabel('功率 / kW');axs[0].legend(ncol=3,fontsize=9)
    axs[1].bar(t,np.array(res['c'])*6,width=1/6,color='#2980b9',label='充电')
    axs[1].bar(t,-np.array(res['d'])*6,width=1/6,color='#cb4335',label='放电')
    axs[1].set_ylabel('储能功率 / kW');axs[1].legend(ncol=2)
    axs[2].plot(np.arange(145)/6,res['e'],color='#1e8449',label='储电量')
    axs[2].axhline(1200,color='gray',ls='--');axs[2].axhline(10800,color='gray',ls='--')
    axs[2].set_ylabel('储电量 / kWh');axs[2].set_xlabel('当日时刻 / h')
    ax=axs[2].twinx();ax.step(t,price,where='post',color='#7d3c98',alpha=.55);ax.set_ylabel('电价 / 元每kWh')
    for a in axs:a.grid(alpha=.2);a.set_xlim(0,24);a.set_xticks(range(0,25,2))
    fig.savefig(OUT/'调度曲线.png',dpi=200);plt.close(fig)
    print(json.dumps({k:res[k] for k in ['cost','purchase','charge','discharge','spill','baseline_cost','savings_pct','blocks','selected','checks','sensitivity']},ensure_ascii=False,indent=2))

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
