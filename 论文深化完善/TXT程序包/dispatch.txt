"""运行与交易结算。输入输出单位沿用论文；发生约束错误时直接报错。"""
from common import *
from data_io import *
from forecasting import *
from optimization import *
from common import _minute


def recourse(g,net,s,eta=.9,capacity=12000):
    # 只使用当前净负荷及库存。先充/放电再补购；输出C,D,R,W和下一库存，均以kWh计。
    """当前时段测量到达后进行局部能量平衡；绝不读取下一时段。"""
    surplus=g-net
    if surplus>=0:
        C=min(surplus,5000*DT,max(0,(capacity*.9-s)/eta));D=R=0.;W=surplus-C
    else:
        D=min(-surplus,5000*DT,max(0,(s-capacity*.1)*eta));C=W=0.;R=-surplus-D
    return C,D,R,W,s+eta*C-D/eta


def merge_emergency_intervals(r,tol=1e-8):
    # 合并相邻紧急购电时段，核验合并前后电量守恒。
    out=[];start=None
    for t in range(len(r)+1):
        active=t<len(r) and r[t]>tol
        if active and start is None:start=t
        if not active and start is not None:out.append((interval(start,t),float(r[start:t].sum())));start=None
    assert abs(sum(x[1] for x in out)-r.sum())<1e-6
    return out


def run_policy(data,fl,fp,margin=.5,terminal=.5,eta=.9,capacity=12000,emergency=5,updates=(),q3=False,price_actual=False,price_forecast=False,fee=.5,refund=True,interp='linear',days=None,s0=None,tag='',save=True):
    # 逐日制定计划并在指定发布时间更新未执行部分；每个10分钟时段实测执行，跨日不重置SOC。save=False禁止导出。
    if days is None:days=range(365)
    days=list(days);s=capacity*.5 if s0 is None else s0;out={k:[] for k in ['G0','G','C','D','R','W','S','plus','minus','PVhat','Lhat','Pdecision']};daily=[];versions=[]
    netactual=(data['L']-data['PV'])*DT
    resid=netactual-(fl-fp)*DT
    for d in days:
        # 正式评价从2月开始。各问题3策略在1月统一按问题2预运行，确保2月初状态可比。
        q3_active=q3 and not (days[0]==0 and d<31)
        p=data['P'][d] if price_actual else data['a'][:,0]
        pp=forecast(data['P'],d,'ma7',data['a'][:,0]) if price_forecast else p
        pv0=fp[d].copy()
        if q3_active:pv0=interpolate_hourly_forecast(data['F'][d,0],data['PV'][d-1,-1] if d else 0,interp)
        pred=(fl[d]-pv0)*DT
        # 问题3用同一发布时刻过去日期的预报残差，避免把日前误差套在临近预报。
        if q3_active:
            hist=[]
            for j in range(max(0,d-30),d):
                pj=interpolate_hourly_forecast(data['F'][j,0],data['PV'][j-1,-1] if j else 0,interp)
                hist.append(netactual[j]-(fl[j]-pj)*DT)
            rs=np.asarray(hist).reshape(-1,T)
        else:rs=resid[:d]
        m=.5 if d<31 and days[0]==0 else margin;term=.5 if d<31 and days[0]==0 else terminal
        N=scenarios(pred,rs,m)
        plan=optimize_day(N,pp,s,eta,capacity,emergency,term);g0=plan['G'].copy();g=g0.copy()
        C=np.zeros(T);D=C.copy();R=C.copy();W=C.copy();plus=C.copy();minus=C.copy();S=np.zeros(T+1);S[0]=s;ph=pv0.copy();lh=fl[d].copy()
        vv=[g0.copy()]
        for t in range(T):
            if q3_active and t in [int(h*6) for h in updates]:
                hour=t//6
                pvnew=interpolate_hourly_forecast(data['F'][d,hour//6],data['PV'][d,t-1],interp)[:T-t]
                rnow=(data['L'][d,max(0,t-6):t]-fl[d,max(0,t-6):t]).mean()
                lnew=np.maximum(0,fl[d,t:]+rnow*np.exp(-np.arange(T-t)/36))
                prednew=(lnew-pvnew)*DT
                rh=[]
                for j in range(max(0,d-30),d):
                    hp=interpolate_hourly_forecast(data['F'][j,hour//6],data['PV'][j,t-1],interp)[:T-t]
                    lr=(data['L'][j,max(0,t-6):t]-fl[j,max(0,t-6):t]).mean()
                    hl=np.maximum(0,fl[j,t:]+lr*np.exp(-np.arange(T-t)/36))
                    rh.append(netactual[j,t:]-(hl-hp)*DT)
                N=scenarios(prednew,np.asarray(rh).reshape(-1,T-t),m)
                pl=optimize_day(N,pp[t:],s,eta,capacity,emergency,term,old=g[t:],fee=fee,refund=refund)
                delta=pl['G']-g[t:];plus[t:]+=np.maximum(delta,0);minus[t:]+=np.maximum(-delta,0);g[t:]=pl['G'];ph[t:]=pvnew;lh[t:]=lnew
                vv.append(g.copy())
            C[t],D[t],R[t],W[t],s=recourse(g[t],netactual[d,t],s,eta,capacity);S[t+1]=s
        base=float(p@g0);inc=float((1+fee)*p@plus);cancel=float(fee*p@minus);ref=float(p@minus) if refund else 0.;em=float(emergency*p@R)
        total=base+inc+cancel-ref+em
        daily.append(dict(day=d,date=str(DATES[d].date()),G0=g0.sum(),G=g.sum(),R=R.sum(),W=W.sum(),base=base,increase=inc,cancel=cancel,refund=ref,adjustment=inc+cancel-ref,emergency=em,total=total,S0=S[0],Send=S[-1],C=C.sum(),D=D.sum(),absolute_adjustment=(plus+minus).sum(),surcharge=fee*float(p@(plus+minus))))
        for key,val in [('G0',g0),('G',g),('C',C),('D',D),('R',R),('W',W),('S',S),('plus',plus),('minus',minus),('PVhat',ph),('Lhat',lh),('Pdecision',pp)]:out[key].append(val)
        versions.append(vv)
        if tag and (d%60==0 or d==days[-1]):print(tag,str(DATES[d].date()),'cost',round(total,2),flush=True)
    out={k:np.asarray(v) for k,v in out.items()};out['days']=np.array(days);out['eta']=np.array(eta);out['capacity']=np.array(capacity);out['multiplier']=np.array(emergency);out['fee']=np.array(fee);out['refund_flag']=np.array(refund)
    df=pd.DataFrame(daily)
    if save and tag:
        np.savez_compressed(ROOT/'results'/f'{tag}.npz',**out);df.to_csv(ROOT/'results'/f'{tag}_daily.csv',index=False,encoding='utf-8-sig')
        dump({str(d):[v.tolist() for v in vv] for d,vv in zip(days,versions) if d in [78,171,265,354]},ROOT/'results'/f'{tag}_versions.json')
    return out,df
