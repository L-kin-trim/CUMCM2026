"""物理与费用验证。输入输出单位沿用论文；发生约束错误时直接报错。"""
from common import *
from data_io import *
from forecasting import *
from optimization import *
from dispatch import *
from common import _minute


def validate_solution(out,data,df,price_actual=False):
    # 从轨迹和实际输入独立重算11类等式及边界；超过1e-6立即失败，不只依赖优化器成功标志。
    ids=out['days'];p=data['P'][ids] if price_actual else np.broadcast_to(data['a'][:,0],(len(ids),T))
    G,C,D,R,W,S=[out[k] for k in ['G','C','D','R','W','S']];eta=float(out['eta']);cap=float(out['capacity']);fee=float(out['fee'])
    bal=G+data['PV'][ids]*DT+D+R-data['L'][ids]*DT-C-W
    expected=(p*out['G0']).sum(axis=1)+(1+fee)*(p*out['plus']).sum(axis=1)+(fee-int(out['refund_flag']))*(p*out['minus']).sum(axis=1)+float(out['multiplier'])*(p*R).sum(axis=1)
    checks={'能量守恒':np.max(np.abs(bal)),'SOC动态':np.max(np.abs(S[:,1:]-S[:,:-1]-eta*C+D/eta)),
            'SOC边界':max(0,cap*.1-S.min(),S.max()-cap*.9),'充放电上限':max(0,C.max()-5000*DT,D.max()-5000*DT),
            '非负':max(0,-min(v.min() for v in [G,C,D,R,W])), '同时充放电':np.minimum(C,D).max(),
            '跨日连续':np.max(np.abs(S[1:,0]-S[:-1,-1])) if np.all(np.diff(ids)==1) and len(ids)>1 else 0.,
            '费用独立核算':np.max(np.abs(expected-df.total.to_numpy())),
            '有效计划交易恒等式':np.max(np.abs(G-out['G0']-out['plus']+out['minus'])),
            '紧急合并守恒':max(abs(sum(v for _,v in merge_emergency_intervals(r))-r.sum()) for r in R),
            '有限数值':float(not all(np.isfinite(x).all() for x in [G,C,D,R,W,S]))}
    result=[dict(检查=k,误差=float(v),状态='PASS' if v<1e-6 else 'FAIL') for k,v in checks.items()]
    assert all(x['状态']=='PASS' for x in result),result
    return result
