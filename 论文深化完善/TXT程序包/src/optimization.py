"""线性规划求解。输入输出单位沿用论文；发生约束错误时直接报错。"""
from common import *
from data_io import *
from forecasting import *
from common import _minute


@lru_cache(maxsize=128)
def lp_structure(n,k,eta):
    # 按G、各情景C/D/R/W/S、终端绝对偏差、增减购电量布局建立稀疏矩阵；按规模和效率缓存。
    # G[n], 各情景(C,D,R,W,S_next)[5n], terminal_abs[k], optional plus/minus[2n]
    nvar=n+k*5*n+k+2*n;A=lil_matrix((2*n*k+n,nvar));b=np.zeros(2*n*k+n)
    for s in range(k):
        off=n+s*5*n
        for t in range(n):
            r=2*n*s+t;A[r,t]=1;A[r,off+t]=-1;A[r,off+n+t]=1;A[r,off+2*n+t]=1;A[r,off+3*n+t]=-1
            r=2*n*s+n+t;A[r,off+4*n+t]=1;A[r,off+t]=-eta;A[r,off+n+t]=1/eta
            if t:A[r,off+4*n+t-1]=-1
    plus=n+k*5*n+k
    for t in range(n):A[2*n*k+t,t]=1;A[2*n*k+t,plus+t]=-1;A[2*n*k+t,plus+n+t]=1
    U=lil_matrix((2*k,nvar))
    for s in range(k):
        z=n+k*5*n+s;end=n+s*5*n+5*n-1
        U[2*s,end]=1;U[2*s,z]=-1;U[2*s+1,end]=-1;U[2*s+1,z]=-1
    return A.tocsr(),U.tocsr()


def optimize_day(net_scenarios,p,s0,eta=.9,capacity=12000,emergency=5,terminal=.5,old=None,fee=.5,refund=True,cyclic=False):
    # 共同计划连接各情景；old为空表示日前，否则对上一有效计划增减。返回计划与首情景状态；该状态不是实际回放。
    N=np.atleast_2d(net_scenarios);k,n=N.shape;p=np.asarray(p);A,U=lp_structure(n,k,eta)
    nv=A.shape[1];c=np.zeros(nv);b=np.zeros(A.shape[0]);bu=np.tile([capacity*.5,-capacity*.5],k)
    weights=np.ones(k)/k;c[:n]=p if old is None else 0
    bounds=[(0,None)]*nv;eps=1e-7
    for s in range(k):
        off=n+s*5*n;b[2*n*s:2*n*s+n]=N[s];b[2*n*s+n]=s0
        c[off:off+2*n]=eps/k;c[off+2*n:off+3*n]=emergency*p*weights[s]
        c[n+k*5*n+s]=terminal*p.mean()*weights[s]
        for t in range(n):
            bounds[off+t]=(0,5000*DT);bounds[off+n+t]=(0,5000*DT)
            bounds[off+4*n+t]=(capacity*.1,capacity*.9)
            if cyclic:bounds[off+2*n+t]=(0,0)
        if cyclic:bounds[off+5*n-1]=(s0,s0)
    plus=n+k*5*n+k
    if old is None:
        # 删除交易关系行；辅助增减量固定零。
        Ause=A[:2*n*k];buse=b[:2*n*k]
        for t in range(2*n):bounds[plus+t]=(0,0)
    else:
        b[2*n*k:]=old;Ause=A;buse=b
        c[plus:plus+n]=(1+fee)*p;c[plus+n:]=(-1+fee if refund else fee)*p
    sol=linprog(c,A_ub=U,b_ub=bu,A_eq=Ause,b_eq=buse,bounds=bounds,method='highs',options={'dual_feasibility_tolerance':1e-8,'primal_feasibility_tolerance':1e-8})
    if not sol.success:raise RuntimeError(sol.message)
    off=n;C=sol.x[off:off+n];D=sol.x[off+n:off+2*n]
    assert np.max(np.minimum(C,D))<1e-5,'同时充放电'
    return dict(G=np.maximum(sol.x[:n],0),C=C,D=D,S=np.r_[s0,sol.x[off+4*n:off+5*n]],objective=sol.fun)
