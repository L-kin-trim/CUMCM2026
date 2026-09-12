"""读取已验证结果绘制论文新增图，不重新拟合或修改模型。"""
from pathlib import Path
import json,csv,datetime,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,FancyArrowPatch

HERE=Path(__file__).resolve().parent
R=HERE.parent/'results'
OUT=HERE/'新增图';OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.sans-serif':['SimSun','Microsoft YaHei'],'axes.unicode_minus':False,'font.size':10,'axes.labelsize':10,'axes.titlesize':10,'legend.fontsize':9,'xtick.labelsize':9,'ytick.labelsize':9,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':300})
blue='#0072B2';orange='#D55E00';green='#009E73';purple='#8B5A9F'
manifest=[]
def save(fig,name,source,desc):
    fig.savefig(OUT/(name+'.png'),dpi=300,bbox_inches='tight',pad_inches=.08,facecolor='white');plt.close(fig)
    manifest.append({'figure':name+'.png','source':source,'meaning':desc})
def clean(ax):ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)

# 1 实体能量流；预测值不是电源，不画成能量输入。
fig,ax=plt.subplots(figsize=(6.3,2.45));ax.set(xlim=(0,10),ylim=(-.4,4));ax.axis('off')
positions={'光伏发电':(1,3),'外部电网':(1,1),'微网母线':(5,2),'小区负载':(9,3),'富余弃置':(9,1),'储能设备':(5,0)}
for txt,(x,y) in positions.items():
    ax.add_patch(Rectangle((x-.85,y-.33),1.7,.66,fc='white',ec=blue,lw=1.3));ax.text(x,y,txt,ha='center',va='center',fontsize=10.5)
def arrow(a,b,label,xy,both=False):
    ax.add_patch(FancyArrowPatch(a,b,arrowstyle='<->' if both else '-|>',mutation_scale=12,lw=1.1,color='#333333'));ax.text(*xy,label,ha='center',va='center',fontsize=9,bbox={'fc':'white','ec':'none','pad':1})
arrow((1.85,3),(4.15,2.2),'光伏电能',(3.1,3.05))
arrow((1.85,1),(4.15,1.8),'常规与紧急购电',(2.8,.85))
arrow((5.85,2.2),(8.15,3),'满足负载',(7,3.05))
arrow((5.85,1.8),(8.15,1),'无售电收益',(7.9,.35))
arrow((5,.34),(5,1.66),'充电 / 放电',(6.1,1.08),True)
save(fig,'01_微网能量流',['C题.md'],'只表示母线能量流；储能双向，弃置无收益。')

# 2 典型日负载、光伏预测与实际值；保持同一日期和时刻轴。
data=np.load(R/'data.npz');forecast=np.load(R/'forecasts.npz');hours=np.arange(144)/6;day=171
fig,axes=plt.subplots(2,1,figsize=(6.3,3.7),sharex=True,layout='constrained')
for ax,key,label in zip(axes,['L','PV'],['(a) 小区负载','(b) 光伏发电']):
    ax.plot(hours,data[key][day],color='#222222',lw=1,label='实际值')
    ax.plot(hours,forecast['ridge_'+key][day],color=blue,ls='--',lw=1,label='日前预测')
    ax.set(ylabel='功率 / kW',title=label,xlim=(0,24));clean(ax)
axes[0].legend(ncol=2,loc='upper left');axes[-1].set(xlabel='日内时刻 / h',xticks=np.arange(0,25,4))
save(fig,'02_典型日预测',['data.npz','forecasts.npz'],'2025-06-21，144个时段，预测仅用此前日期。')

# 3 月度紧急购电对比，统一以万kWh计量。
months=np.array([(datetime.date(2025,1,1)+datetime.timedelta(days=i)).month for i in range(365)])
fig,ax=plt.subplots(figsize=(6.3,2.8),layout='constrained');monthly=[]
for i,(tag,label,col) in enumerate([('q2','问题2',blue),('q3_D','问题3策略D',orange)]):
    z=np.load(R/(tag+'.npz'));v=[float(z['R'][months==m].sum())/10000 for m in range(2,13)]
    ax.bar(np.arange(11)+(i-.5)*.36,v,.36,label=label,color=col)
    monthly.append({'model':tag,'months':list(range(2,13)),'emergency_10kwh':v})
ax.set(xticks=range(11),xticklabels=range(2,13),xlabel='月份',ylabel='紧急购电量 / 万kWh');ax.legend(ncol=2);clean(ax)
save(fig,'03_月度紧急购电',['q2.npz','q3_D.npz'],'按月累加10分钟紧急电量，不比较不同单位费用。')
(OUT/'月度汇总.json').write_text(json.dumps(monthly,ensure_ascii=False,indent=2),encoding='utf-8')

# 4 每次更新相对上一有效计划的差额；区分已经执行的区间。
versions=np.array(json.loads((R/'q3_D_versions.json').read_text(encoding='utf-8'))[str(day)])
delta=np.diff(versions,axis=0);mask=np.zeros_like(delta,dtype=bool)
for i,start in enumerate([36,72,108]):mask[i,:start]=True
delta=np.ma.array(delta,mask=mask);bound=float(np.max(np.abs(delta)))
fig,ax=plt.subplots(figsize=(6.3,2.3),layout='constrained');cmap=plt.get_cmap('RdBu_r').copy();cmap.set_bad('#E5E5E5')
im=ax.imshow(delta,aspect='auto',interpolation='nearest',extent=(0,24,2.5,-.5),cmap=cmap,vmin=-bound,vmax=bound)
ax.set(yticks=[0,1,2],yticklabels=['6时更新','12时更新','18时更新'],xticks=np.arange(0,25,3),xlabel='计划执行时刻 / h')
cb=fig.colorbar(im,ax=ax,pad=.02,shrink=.9);cb.set_label('增减电量 / kWh')
save(fig,'04_滚动调整热力图',['q3_D_versions.json'],'2025-06-21；红色增购，蓝色减购，灰色已执行；相邻版本差额。')

# 5 波动电价、购电、库存共用时刻轴，电量与功率不混用。
z=np.load(R/'q43_D.npz');fig,axes=plt.subplots(3,1,figsize=(6.3,4.0),sharex=True,layout='constrained')
axes[0].plot(hours,data['P'][day],color=orange,lw=1.2);axes[0].set(ylabel='电价\n元/kWh')
axes[1].step(hours,z['G'][day],where='post',color=blue,lw=1);axes[1].set(ylabel='时段购电量\nkWh')
axes[2].plot(np.arange(145)/6,z['S'][day],color=green,lw=1.2)
for boundary in [1200,10800]:axes[2].axhline(boundary,color='#666666',ls='--',lw=.7)
axes[2].set(ylabel='储电量\nkWh',xlabel='日内时刻 / h',xticks=np.arange(0,25,4),ylim=(0,12000))
for ax in axes:ax.set_xlim(0,24);clean(ax)
save(fig,'05_电价购电储能联动',['data.npz','q43_D.npz'],'2025-06-21，问题4-3策略D，当日价格曲线已知条件；虚线为库存边界。')

# 6 与正文敏感性表保持同一24天口径。
with (R/'敏感性24日.csv').open(encoding='utf-8-sig') as f:rec={r['case']:r for r in csv.DictReader(f) if r['model']=='q3_D'}
base=float(rec['baseline']['inventory_adjusted_cost'])
cases=[('eta085','效率各85%'),('eta095','效率各95%'),('capacity9600','容量9600 kWh'),('capacity14400','容量14400 kWh'),('margin1','残差裕度1'),('no_refund','取消不退款')]
changes=[(float(rec[k]['inventory_adjusted_cost'])/base-1)*100 for k,_ in cases]
fig,ax=plt.subplots(figsize=(6.3,2.65),layout='constrained');bars=ax.barh([label for _,label in cases],changes,color=[orange if v>0 else blue for v in changes],height=.62)
ax.axvline(0,color='#333333',lw=.8);ax.bar_label(bars,labels=[f'{v:+.2f}%' for v in changes],padding=4,fontsize=9)
ax.invert_yaxis();ax.set(xlabel='库存校正费用相对基准的变化 / %',xlim=(-6,9));ax.grid(axis='x',alpha=.2);ax.set_axisbelow(True)
save(fig,'06_敏感性对比',['敏感性24日.csv'],'仅24个代表日的策略D；不外推为全年收益。')
for entry in manifest:
    entry['input_sha256']={name:hashlib.sha256((R/name).read_bytes()).hexdigest() for name in entry['source'] if (R/name).exists()}
(OUT/'图形溯源.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('Created',len(manifest),'figures')
