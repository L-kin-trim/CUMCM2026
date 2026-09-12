"""四方面检验与风险惩罚扩展。固定种子；原结果只读；不改写提交表。"""
from pathlib import Path
import sys, inspect, json
import numpy as np
import pandas as pd
from scipy.sparse import hstack, vstack, csr_matrix
HERE=Path(__file__).resolve().parent
WORK=HERE.parents[1]
SRC=WORK/'审查与完善/07_复现代码与数据/src'
sys.path.insert(0,str(SRC))
import model as m
R=SRC.parent/'results'
OUT=HERE.parent/'检验结果';OUT.mkdir(exist_ok=True)

ORIGINAL_OPTIMIZER=m.optimize_day
def risk_solver(weight):
    """增加最坏情景紧急费用变量 z；目标为原目标加 weight*z，仍为 LP。"""
    source=inspect.getsource(ORIGINAL_OPTIMIZER)
    insertion='''
    if risk_weight > 0:
        # 最后一列是最坏情景损失上界；情景共同日前计划保持不变。
        c=np.r_[c,risk_weight];bounds=bounds+[(0,None)]
        Ause=hstack([Ause,csr_matrix((Ause.shape[0],1))],format='csr')
        U=hstack([U,csr_matrix((U.shape[0],1))],format='csr')
        tail=np.zeros((k,nv+1))
        for ss in range(k):
            off0=n+ss*5*n
            tail[ss,off0+2*n:off0+3*n]=emergency*p
            tail[ss,-1]=-1
        U=vstack([U,csr_matrix(tail)],format='csr');bu=np.r_[bu,np.zeros(k)]
'''
    source=source.replace('    sol=linprog(',insertion+'    sol=linprog(')
    ns=dict(vars(m),risk_weight=weight,hstack=hstack,vstack=vstack,csr_matrix=csr_matrix)
    exec(compile(source,'risk_optimize_day','exec'),ns)
    return ns['optimize_day']

def evaluate_risk(data,fl,fp):
    """权重只在1月选择；随后在预先指定的四季24日验证，初态一致。"""
    original=m.optimize_day;records=[]
    try:
        for w in [0,.1,.3,1.]:
            m.optimize_day=risk_solver(w) if w else original
            _,df=m.run_policy(data,fl,fp,days=range(16,31),s0=6000,q3=True,updates=(6,12,18),margin=0,save=False)
            cost=df.total.sum()-.5*data['a'][:,0].mean()*(df.Send.iloc[-1]-6000)
            records.append(dict(stage='1月验证',weight=w,cost=cost,emergency=df.emergency.sum()))
            print('risk validation',records[-1],flush=True)
        selected=min(records,key=lambda x:x['cost'])['weight']
        # 同时报告各候选的外样本表现，不用外样本重新选择权重。
        for w in [0,.1,.3,1.]:
            m.optimize_day=risk_solver(w) if w else original
            cost=em=0.;checks=[]
            for start in [76,169,263,352]:
                initial=float(np.load(R/'q3_D.npz')['S'][start,0])
                out,df=m.run_policy(data,fl,fp,days=range(start,start+6),s0=initial,q3=True,updates=(6,12,18),margin=0,save=False)
                checks+=m.validate_solution(out,data,df)
                cost+=df.total.sum()-.5*data['a'][:,0].mean()*(df.Send.iloc[-1]-initial)
                em+=df.emergency.sum()
            records.append(dict(stage='四季24日',weight=w,cost=cost,emergency=em))
            print('risk test',records[-1],flush=True)
        pd.DataFrame(records).to_csv(OUT/'风险模型对比.csv',index=False,encoding='utf-8-sig')
        return dict(selected_weight=selected,records=records)
    finally:m.optimize_day=original

def fixed_plan_stress(data):
    """冻结已制定的常规计划，在实际净负荷受扰动时连续执行实时电池控制。"""
    z=np.load(R/'q3_D.npz');g=z['G'][31:];p=data['a'][:,0]
    records=[]
    for label,lf,pvf in [('原始负荷',1,1),('负载增加5%',1.05,1),('光伏减少10%',1,.9),('联合不利扰动',1.05,.9)]:
        s=float(z['S'][31,0]);em=0.;energy=0.;smin=smax=s;res=0.
        for j,d in enumerate(range(31,365)):
            for t in range(144):
                net=(lf*data['L'][d,t]-pvf*data['PV'][d,t])/6
                c,dd,r,w,s=m.recourse(g[j,t],net,s)
                em+=5*p[t]*r;energy+=r;smin=min(smin,s);smax=max(smax,s)
                res=max(res,abs(g[j,t]+dd+r-net-c-w))
        records.append(dict(case=label,emergency_kwh=energy,emergency_cost=em,min_soc=smin,max_soc=smax,balance_error=res,end_soc=s))
    pd.DataFrame(records).to_csv(OUT/'固定计划压力检验.csv',index=False,encoding='utf-8-sig')
    return records

def errors_and_comparison(data,fl,fp):
    """误差按整日聚合；比较采用配对的7日移动区块重采样，保留短期相关性。"""
    e=((fl-fp)-(data['L']-data['PV']))[31:]
    metrics=dict(MAE=float(np.abs(e).mean()),RMSE=float(np.sqrt((e**2).mean())),bias=float(e.mean()),p95_abs=float(np.quantile(np.abs(e),.95)))
    np.savez_compressed(OUT/'误差数组.npz',net_error=e)
    a=pd.read_csv(R/'q3_A_daily.csv').iloc[31:];d=pd.read_csv(R/'q3_D_daily.csv').iloc[31:]
    # 同一终端库存价值逐日校正，避免跨日库存差异混入收益。
    price=.5*data['a'][:,0].mean()
    gain=(a.total-price*(a.Send-a.S0))-(d.total-price*(d.Send-d.S0))
    gain=gain.to_numpy();rng=np.random.default_rng(20260912);means=[]
    for _ in range(2000):
        ix=np.concatenate([np.arange(s,s+7) for s in rng.integers(0,len(gain)-6,size=48)])[:len(gain)]
        means.append(gain[ix].mean())
    ci=np.quantile(means,[.025,.975])
    comp=dict(mean_gain=float(gain.mean()),ci_low=float(ci[0]),ci_high=float(ci[1]),positive_days=int((gain>0).sum()),days=len(gain),replicates=2000,block_days=7)
    pd.DataFrame(dict(date=d.date,gain=gain)).to_csv(OUT/'日费用配对差.csv',index=False,encoding='utf-8-sig')
    np.savez_compressed(OUT/'区块重采样.npz',means=means)
    return metrics,comp

def main():
    data=dict(np.load(R/'data.npz'));fc=np.load(R/'forecasts.npz');fl=fc['ridge_L'].copy();fp=fc['ridge_PV'].copy()
    # 沿用既有1月预运行信息，不改变历史状态。
    fl[:31]=fc['ewma_L'][:31];fp[:31]=fc['ewma_PV'][:31]
    metrics,comparison=errors_and_comparison(data,fl,fp)
    result=dict(errors=metrics,comparison=comparison,stress=fixed_plan_stress(data),risk=evaluate_risk(data,fl,fp))
    (OUT/'新增检验汇总.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
