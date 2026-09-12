"""因果预测与误差。输入输出单位沿用论文；发生约束错误时直接报错。"""
from common import *
from data_io import *
from common import _minute


def forecast(y,d,method,fallback):
    # 仅以目标日前的样本预测；参数method选择六种方法，fallback处理无历史情形。返回144个功率值。
    """只能访问 y[:d]；不同候选均遵循相同截止点。"""
    if d==0:return fallback.copy()
    h=y[:d]
    if method=='mean':v=h.mean(axis=0)
    elif method.startswith('ma'):v=h[-int(method[2:]):].mean(axis=0)
    elif method=='ewma':
        weight=.8**np.arange(min(d,30)-1,-1,-1);v=np.average(h[-30:],axis=0,weights=weight)
    else:
        if d<12:return forecast(y,d,'ma7',fallback)
        def feat(j):
            return np.stack([np.ones(T),y[j-1]/5000,y[j-7]/5000,y[max(0,j-7):j].mean(axis=0)/5000,
                             np.full(T,np.sin(2*np.pi*j/7)),np.full(T,np.cos(2*np.pi*j/7))],axis=1)
        idx=range(max(7,d-60),d);X=np.concatenate([feat(j) for j in idx]);z=y[list(idx)].reshape(-1)/5000
        reg=np.eye(X.shape[1])*1.;reg[0,0]=1e-6
        coef=np.linalg.solve(X.T@X+reg,X.T@z);v=feat(d)@coef*5000
        # 用历史范围裁剪外推，禁止用当日实际值设定上下界。
        v=np.clip(v,0,np.maximum(h[-30:].max(axis=0)*1.3,1.))
    return np.maximum(v,0)


def build_forecasts(data):
    # 对365日逐一调用因果预测器；生成所有候选，不用外样本选择模型。
    out={}
    for m in METHODS:
        out[m]={}
        for k,col in [('L',1),('PV',2)]:
            out[m][k]=np.stack([forecast(data[k],d,m,data['a'][:,col]) for d in range(365)])
    return out


def metrics(pred,actual):
    # 返回MAE、RMSE、归一化MAE和避开近零实际值的MAPE；功率误差单位kW。
    e=pred-actual;mask=actual>max(1,float(actual.max())*.01)
    return dict(MAE=float(np.abs(e).mean()),RMSE=float(np.sqrt((e*e).mean())),nMAE=float(np.abs(e).mean()/max(actual.mean(),1)),MAPE=float(np.mean(np.abs(e[mask]/actual[mask]))*100))


def interpolate_hourly_forecast(values,anchor,method='linear'):
    # 用发布时间已知的左端锚点插值整点预报；返回10分钟分辨率未来24小时功率。
    x=np.arange(25);y=np.r_[anchor,values];q=np.arange(1,145)/6
    v=np.interp(q,x,y) if method=='linear' else PchipInterpolator(x,y)(q)
    return np.maximum(v,0)


def scenarios(pred,residuals,margin=.5):
    # 从最近30个完整日残差按日总量排序选代表曲线；margin乘标准差，保持日内相关结构。
    # 最近历史预测残差的真实整日曲线按全天净能量排序选三条代表；不读取目标日。
    if len(residuals)<3:return pred[None,:]
    r=residuals[-30:];order=np.argsort(r.sum(axis=1));ix=np.rint(np.array([.15,.5,.85])*(len(r)-1)).astype(int)
    return pred[None,:]+r[order[ix]]+margin*r.std(axis=0)[None,:]
