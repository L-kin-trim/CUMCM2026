from model import *
import argparse, time

def main(stage):
    data=load_data()
    if stage in ['all','q1']:
        a=data['a'];r=optimize_day((a[:,1]-a[:,2])*DT,a[:,0],6000,cyclic=True,terminal=0)
        G,C,D,S=[r[x] for x in ['G','C','D','S']];W=G+a[:,2]*DT+D-a[:,1]*DT-C
        assert W.min()>-1e-6 and abs(S[-1]-6000)<1e-6
        np.savez_compressed(ROOT/'results'/'q1.npz',G=G,C=C,D=D,S=S,W=W)
        summary=dict(total_energy=G.sum(),cost=a[:,0]@G,initial=S[0],final=S[-1],max_balance_error=float(np.max(np.abs(G+a[:,2]*DT+D-a[:,1]*DT-C-W))),no_battery_cost=float(a[:,0]@np.maximum((a[:,1]-a[:,2])*DT,0)),six_slots={interval(t):G[t] for t in [60,72,84,96,108,120]})
        # 左端样本、日内周期闭合的另一解释，仅作时间敏感性，不用于主模板。
        alt=np.roll(a,1,axis=0);rr=optimize_day((alt[:,1]-alt[:,2])*DT,alt[:,0],6000,cyclic=True,terminal=0)
        summary['left_endpoint_alternative_cost']=alt[:,0]@rr['G']
        dump(summary,ROOT/'results'/'q1_summary.json');print('Q1',summary,flush=True)
        pd.DataFrame([dict(区间=interval(t,t+24),充电量=C[t:t+24].sum(),放电量=D[t:t+24].sum()) for t in range(0,144,24)]).to_csv(ROOT/'results'/'表2_问题1.csv',index=False,encoding='utf-8-sig')
        if stage=='q1':return
    if stage in ['all','forecast']:
        forecasts=build_forecasts(data)
        np.savez_compressed(ROOT/'results'/'forecasts.npz',**{m+'_'+k:v for m,dic in forecasts.items() for k,v in dic.items()})
        rows=[]
        for m in METHODS:
            for k in ['L','PV']:
                for period,sl in [('1月滚动验证',slice(16,31)),('2月至12月外样本',slice(31,None))]:
                    rows.append(dict(method=m,variable=k,period=period,**metrics(forecasts[m][k][sl],data[k][sl])))
        pd.DataFrame(rows).to_csv(ROOT/'results'/'预测精度.csv',index=False,encoding='utf-8-sig')
        # 固定相同初始SOC，连续15日经济回测；不重置每一天的SOC。
        tune=[]
        for m in METHODS:
            for margin in [0.,.5,1.]:
                for terminal in [0.,.5,1.]:
                    _,df=run_policy(data,forecasts[m]['L'],forecasts[m]['PV'],margin=margin,terminal=terminal,days=range(16,31),save=False)
                    tune.append(dict(method=m,margin=margin,terminal=terminal,cost=df.total.sum(),R=df.R.sum(),Send=df.Send.iloc[-1]))
            print('tuned',m,flush=True)
        td=pd.DataFrame(tune);td['inventory_adjusted_cost']=td.cost-.5*data['a'][:,0].mean()*(td.Send-6000)
        td=td.sort_values('inventory_adjusted_cost');td.to_csv(ROOT/'results'/'1月经济选型.csv',index=False,encoding='utf-8-sig')
        selected=td.iloc[0].to_dict();dump(selected,ROOT/'results'/'selected.json');print('SELECTED',selected,flush=True)
        if stage=='forecast':return
    f=np.load(ROOT/'results'/'forecasts.npz');selected=json.loads((ROOT/'results'/'selected.json').read_text(encoding='utf-8'))
    m=selected['method'];fl=f[m+'_L'].copy();fp=f[m+'_PV'].copy()
    # 所有正式策略1月统一使用事先固定 EWMA；不会用1月末选型反写1月的SOC。
    fl[:31]=f['ewma_L'][:31];fp[:31]=f['ewma_PV'][:31]
    common=dict(margin=selected['margin'],terminal=selected['terminal'])
    if stage in ['all','annual','annual_force']:
        validations=[];summaries=[]
        experiments=[('q2',False,False,()),('q3_A',True,False,()),('q3_B',True,False,(6,)),('q3_C',True,False,(6,12)),('q3_D',True,False,(6,12,18)),('q42',False,True,()),('q43_A',True,True,()),('q43_B',True,True,(6,)),('q43_C',True,True,(6,12)),('q43_D',True,True,(6,12,18)),('q42_causal_price',False,True,()),('q43_causal_price',True,True,(6,12,18))]
        for tag,q3,pa,updates in experiments:
            if stage!='annual_force' and (ROOT/'results'/f'{tag}.npz').exists():
                out=dict(np.load(ROOT/'results'/f'{tag}.npz'));df=pd.read_csv(ROOT/'results'/f'{tag}_daily.csv')
            else:out,df=run_policy(data,fl,fp,**common,q3=q3,price_actual=pa,price_forecast='causal' in tag,updates=updates,tag=tag)
            validations.extend([dict(model=tag,**v) for v in validate_solution(out,data,df,pa)])
            agg=df[df.day>=31].select_dtypes('number').sum().to_dict();agg.pop('day');agg.pop('S0');agg.pop('Send')
            summaries.append(dict(model=tag,**agg,initial_Feb=out['S'][31,0],final_Dec=out['S'][-1,-1]))
            pd.DataFrame(validations).to_csv(ROOT/'audit'/'物理与费用验证.csv',index=False,encoding='utf-8-sig')
            pd.DataFrame(summaries).to_csv(ROOT/'results'/'年度汇总.csv',index=False,encoding='utf-8-sig')
    if stage in ['all','sensitivity']:
        # 24个连续代表日：四季各6日，初值取主策略同日已实现SOC；同一组比较统一初值。
        starts=[76,169,263,352];rows=[]
        cases=[('baseline',{}),('eta085',{'eta':.85}),('eta095',{'eta':.95}),('roundtrip090',{'eta':np.sqrt(.9)}),('capacity9600',{'capacity':9600}),('capacity14400',{'capacity':14400}),('capacity18000',{'capacity':18000}),('emergency3',{'emergency':3}),('emergency7',{'emergency':7}),('margin0',{'margin':0}),('margin1',{'margin':1}),('terminal0',{'terminal':0}),('terminal1',{'terminal':1}),('fee025',{'fee':.25}),('fee075',{'fee':.75}),('no_refund',{'refund':False}),('pchip',{'interp':'pchip'}),('error150',{})]
        for tag,q3 in [('q2',False),('q3_D',True)]:
            base=np.load(ROOT/'results'/f'{tag}.npz')
            for name,kw in cases:
                if not q3 and name in ['fee025','fee075','no_refund','pchip']:continue
                opt=common|kw;cost=em=ener=spill=0.;value=0.
                for start in starts:
                    load=fl.copy();pv=fp.copy()
                    # 压力试验只改变当时已可用预测的振幅，不读取当日实际误差。
                    if name=='error150':load=load*1.10;pv=pv*.90
                    cap=opt.get('capacity',12000);sinit=float(np.clip(base['S'][start,0],cap*.1,cap*.9))
                    o,d=run_policy(data,load,pv,**opt,q3=q3,updates=(6,12,18) if q3 else (),days=range(start,start+6),s0=sinit,save=False)
                    validate_solution(o,data,d);cost+=d.total.sum();em+=d.emergency.sum();ener+=d.R.sum();spill+=d.W.sum();value+=.5*data['a'][:,0].mean()*(d.Send.iloc[-1]-sinit)
                rows.append(dict(model=tag,case=name,cost=cost,inventory_adjusted_cost=cost-value,emergency=em,R=ener,W=spill))
                print('sensitivity',tag,name,round(cost,2),flush=True)
        pd.DataFrame(rows).to_csv(ROOT/'results'/'敏感性24日.csv',index=False,encoding='utf-8-sig')
    print('DONE',stage,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',default='all');main(p.parse_args().stage)
