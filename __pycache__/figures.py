from model import *
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from PIL import Image,ImageOps,ImageDraw
import platform

plt.rcParams.update({'font.sans-serif':['Microsoft YaHei','SimHei','Arial Unicode MS'],'axes.unicode_minus':False,'figure.dpi':120,'savefig.dpi':300,'axes.grid':True,'grid.alpha':.25,'legend.frameon':False,'pdf.fonttype':42})
COL=['#0072B2','#D55E00','#009E73','#CC79A7','#E69F00','#56B4E9']
data=load_data();a=data['a'];f=np.load(ROOT/'results'/'forecasts.npz');q1=np.load(ROOT/'results'/'q1.npz')
outs={k:np.load(ROOT/'results'/f'{k}.npz') for k in ['q2','q3_A','q3_B','q3_C','q3_D','q42','q43_D']}
daily={k:pd.read_csv(ROOT/'results'/f'{k}_daily.csv') for k in outs}
summary=pd.read_csv(ROOT/'results'/'年度汇总.csv');sens=pd.read_csv(ROOT/'results'/'敏感性24日.csv')
hours=np.arange(T)/6;figdata={};alts={}
def save(fig,n,title,alt,table=None):
    path=ROOT/'figures'/f'图{n:02d}_{title}.png';fig.savefig(path,facecolor='white');plt.close(fig)
    alts[path.name]=alt
    if table is not None:pd.DataFrame(table).to_csv(ROOT/'figures'/f'图{n:02d}_数据.csv',index=False,encoding='utf-8-sig')
def figax(n=1,figsize=(8.5,5.2)):
    return plt.subplots(n,1,figsize=figsize,layout='constrained',squeeze=False)

# 1
fig,ax=plt.subplots(figsize=(9,4.5),layout='constrained');ax.axis('off')
nodes={'光伏预测/实测':(.05,.65),'外部电网':(.05,.25),'储能系统':(.42,.15),'微网母线':(.42,.62),'小区负载':(.78,.62),'预测与优化控制器':(.42,.87)}
for label,(x,y) in nodes.items():ax.add_patch(FancyBboxPatch((x,y),.18,.11,boxstyle='round,pad=.02',fc='#F5F5F5',ec=COL[0],lw=1.6));ax.text(x+.09,y+.055,label,ha='center',va='center',fontsize=10)
for u,v,label in [('光伏预测/实测','微网母线','光伏'),('外部电网','微网母线','常规/紧急购电'),('储能系统','微网母线','充放电'),('微网母线','小区负载','供电'),('预测与优化控制器','微网母线','购电指令'),('预测与优化控制器','储能系统','SOC约束')]:
    x1,y1=nodes[u];x2,y2=nodes[v];ax.add_patch(FancyArrowPatch((x1+.18,y1+.055),(x2,y2+.055),arrowstyle='-|>',mutation_scale=12,color='#555',connectionstyle='arc3,rad=.08'));ax.text((x1+x2+.18)/2,(y1+y2+.11)/2,label,fontsize=8,ha='center',bbox=dict(fc='white',ec='none',alpha=.8))
save(fig,1,'能量流与控制结构','光伏和外网经微网母线供给负载，储能双向连接，控制器使用预测和SOC约束发出购电与充放电指令。')
# 2
fig,axs=plt.subplots(2,1,figsize=(9,6),layout='constrained',sharex=True);axs[0].plot(hours,a[:,1],label='负载',c=COL[0]);axs[0].plot(hours,a[:,2],label='光伏',c=COL[2],ls='--');axs[0].set_ylabel('功率（kW）');axs[0].legend();axs[1].plot(hours,a[:,0],c=COL[1]);axs[1].set(xlabel='时刻（h）',ylabel='电价（元/kWh）',xlim=(0,24));save(fig,2,'附件1日内曲线','上图展示一天负载和光伏，下图展示电价；光伏仅在白天产生，电价分时波动。',dict(时刻=hours,负载=a[:,1],光伏=a[:,2],电价=a[:,0]))
# 3
fig,axs=plt.subplots(2,1,figsize=(9,6),layout='constrained',sharex=True);axs[0].plot(hours,q1['G'],label='购电量',c=COL[0]);axs[0].plot(hours,q1['C'],label='充电量',c=COL[2]);axs[0].plot(hours,-q1['D'],label='放电量（负向显示）',c=COL[1]);axs[0].set_ylabel('10 min电量（kWh）');axs[0].legend(ncol=3);axs[1].plot(np.arange(145)/6,q1['S'],c=COL[3]);axs[1].axhspan(1200,10800,color=COL[2],alpha=.08);axs[1].set(xlabel='时刻（h）',ylabel='储电量（kWh）',xlim=(0,24));save(fig,3,'问题1最优调度','购电、充放电与SOC的最优日内轨迹；SOC在0时和24时均为6000 kWh。',dict(时刻=hours,购电=q1['G'],充电=q1['C'],放电=q1['D'],SOC=q1['S'][:-1]))
# 4
months=np.array([d.month for d in DATES]);tab=[]
for m in range(1,13):tab.append([m,data['L'][months==m].mean(),data['PV'][months==m].mean()])
tab=np.array(tab);fig,ax=plt.subplots(figsize=(9,5),layout='constrained');ax.plot(tab[:,0],tab[:,1],marker='o',label='平均负载',c=COL[0]);ax.plot(tab[:,0],tab[:,2],marker='s',label='平均光伏',c=COL[2]);ax.set(xlabel='月份',ylabel='平均功率（kW）',xticks=range(1,13));ax.legend();save(fig,4,'全年月度统计','负载与光伏的月均功率随季节变化。',dict(月份=tab[:,0],平均负载=tab[:,1],平均光伏=tab[:,2]))
# 5/6 typical
d=171;fig,ax=plt.subplots(figsize=(9,5),layout='constrained');ax.plot(hours,data['L'][d],label='实际',c='black');ax.plot(hours,f['ridge_L'][d],label='岭回归预测',c=COL[0],ls='--');ax.set(xlabel='时刻（h）',ylabel='负载功率（kW）',title=str(DATES[d].date()),xlim=(0,24));ax.legend();save(fig,5,'负载预测效果','2025年6月21日岭回归负载预测与实际曲线对比。',dict(时刻=hours,实际=data['L'][d],预测=f['ridge_L'][d]))
fig,ax=plt.subplots(figsize=(9,5),layout='constrained');ax.plot(hours,data['PV'][d],label='实际',c='black');ax.plot(hours,f['ridge_PV'][d],label='岭回归预测',c=COL[2],ls='--');ax.set(xlabel='时刻（h）',ylabel='光伏功率（kW）',title=str(DATES[d].date()),xlim=(0,24));ax.legend();save(fig,6,'光伏预测效果','2025年6月21日岭回归光伏预测与实际曲线对比。',dict(时刻=hours,实际=data['PV'][d],预测=f['ridge_PV'][d]))
#7
res=((f['ridge_L'][31:]-f['ridge_PV'][31:])-(data['L'][31:]-data['PV'][31:]))*DT
fig,ax=plt.subplots(figsize=(8,5),layout='constrained');ax.hist(res.ravel(),bins=60,color=COL[0],alpha=.8);ax.axvline(0,c='black',lw=1);ax.set(xlabel='净负荷预测误差（kWh/10 min）',ylabel='频数');save(fig,7,'净负荷预测残差分布','2月至12月净负荷预测误差分布，零线用于识别系统偏差。',dict(误差=res.ravel()))
#8
fig,axs=plt.subplots(2,2,figsize=(11,7),layout='constrained',sharex=True);typ=[78,171,265,354]
for ax,d in zip(axs.flat,typ):ax.plot(hours,outs['q2']['G0'][d],label='日前购电',c=COL[0]);ax.plot(hours,(data['L'][d]-data['PV'][d])*DT,label='实际净负荷',c='black',alpha=.75);ax.set_title(str(DATES[d].date()));ax.set_ylabel('电量（kWh/10 min）')
axs[1,0].set_xlabel('时刻（h）');axs[1,1].set_xlabel('时刻（h）');axs[0,0].legend();save(fig,8,'典型日计划与净负荷','四个指定日期问题2日前购电与实际净负荷对比。')
#9
dd=daily['q2'].copy();dd['month']=pd.to_datetime(dd.date).dt.month;tab=dd[dd.day>=31].groupby('month')[['R','emergency']].sum()
fig,axs=plt.subplots(2,1,figsize=(9,6),layout='constrained',sharex=True);axs[0].bar(tab.index,tab.R,color=COL[0]);axs[0].set_ylabel('紧急购电量（kWh）');axs[1].bar(tab.index,tab.emergency,color=COL[1]);axs[1].set(xlabel='月份',ylabel='紧急购电费（元）',xticks=range(1,13));save(fig,9,'紧急购电月度统计','问题2紧急购电量与费用的月度总计。',tab.reset_index())
#10
pv_rm=[]
for issue in [0,6,12,18]:
    errors=[]
    for d in range(31,365):
        pred=interpolate_hourly_forecast(data['F'][d,issue//6],data['PV'][d,issue*6-1] if issue else data['PV'][d-1,-1])[:T-issue*6]
        errors.extend(pred-data['PV'][d,issue*6:])
    pv_rm.append([issue,np.mean(np.abs(errors)),np.sqrt(np.mean(np.square(errors)))])
pv_rm=np.array(pv_rm);fig,ax=plt.subplots(figsize=(8,5),layout='constrained');x=np.arange(4);ax.bar(x-.18,pv_rm[:,1],.36,label='MAE',color=COL[0]);ax.bar(x+.18,pv_rm[:,2],.36,label='RMSE',color=COL[1]);ax.set(xlabel='预报发布时间',ylabel='光伏预测误差（kW）',xticks=x,xticklabels=['0:00','6:00','12:00','18:00']);ax.legend();save(fig,10,'分时光伏预报误差','不同发布时间对当天剩余时段的光伏预测误差；后续预报的有效预测区间更短。',dict(时刻=pv_rm[:,0],MAE=pv_rm[:,1],RMSE=pv_rm[:,2]))
#11 versions
v=json.loads((ROOT/'results'/'q3_D_versions.json').read_text(encoding='utf-8'));vv=np.asarray(v['171']);fig,ax=plt.subplots(figsize=(9,5),layout='constrained')
for i,row in enumerate(vv):ax.plot(hours,row,label=['0:00计划','6:00版','12:00版','18:00版'][i],c=COL[i],ls=['-','--','-.',':'][i]);ax.set(xlabel='时刻（h）',ylabel='常规购电量（kWh/10 min）',title='2025-06-21');ax.legend(ncol=2);save(fig,11,'滚动购电调整','典型日四个版本购电曲线；更新仅影响发布时刻之后的区间。')
#12
sub=summary[summary.model.isin(['q3_A','q3_B','q3_C','q3_D'])].copy();fig,ax=plt.subplots(figsize=(8,5),layout='constrained');bars=ax.bar(sub.model,sub.total/1e6,color=COL[:4]);ax.bar_label(bars,fmt='%.3f');ax.set(xlabel='预报更新策略',ylabel='2—12月总成本（百万元）');save(fig,12,'预报更新策略成本','策略D成本最低，策略A最高，展示增加预报更新的经济价值。',sub[['model','total','emergency','adjustment']])
#13
d=171;o=outs['q43_D'];fig,axs=plt.subplots(3,1,figsize=(9,7),layout='constrained',sharex=True);axs[0].plot(hours,data['P'][d],c=COL[1]);axs[0].set_ylabel('电价（元/kWh）');axs[1].plot(hours,o['G'][d],c=COL[0]);axs[1].set_ylabel('购电量（kWh）');axs[2].plot(np.arange(145)/6,o['S'][d],c=COL[3]);axs[2].set(xlabel='时刻（h）',ylabel='SOC（kWh）',xlim=(0,24));save(fig,13,'波动电价调度关系','2025年6月21日波动电价、最终购电量和SOC的对齐轨迹。')
#14 average day
vals=[json.loads((ROOT/'results'/'q1_summary.json').read_text(encoding='utf-8'))['cost']]+[summary.set_index('model').loc[k,'total']/334 for k in ['q2','q3_D','q42','q43_D']]
fig,ax=plt.subplots(figsize=(8.5,5),layout='constrained');bars=ax.bar(['问题1单日','问题2','问题3','问题4-2','问题4-3'],np.array(vals)/1e4,color=COL[:5]);ax.bar_label(bars,fmt='%.2f');ax.set_ylabel('平均日成本（万元）');save(fig,14,'各问题成本对比','问题1展示附件1单日结果，其余为2月至12月平均日成本，口径在图中统一为日均。',dict(模型=['Q1','Q2','Q3','Q4-2','Q4-3'],平均日成本=vals))
#15
sub=sens[(sens.model=='q3_D') & sens['case'].isin(['baseline','eta085','eta095','capacity9600','capacity14400','emergency3','emergency7','margin1','fee025','fee075'])].copy();base=float(sub[sub['case']=='baseline'].inventory_adjusted_cost.iloc[0]);sub['变化率']=(sub.inventory_adjusted_cost/base-1)*100
fig,ax=plt.subplots(figsize=(9,5.5),layout='constrained');colors=[COL[1] if x>0 else COL[2] for x in sub.变化率];bars=ax.barh(sub['case'],sub.变化率,color=colors);ax.axvline(0,c='black',lw=1);ax.bar_label(bars,fmt='%+.1f%%');ax.set(xlabel='相对基准的库存价值校正成本变化（%）',ylabel='敏感性情景');save(fig,15,'敏感性分析','24个代表日上，效率、容量、紧急倍率、安全裕度和调整费的成本影响。',sub)

manifest={'created_at':pd.Timestamp.now().isoformat(),'seed':SEED,'matplotlib':matplotlib.__version__,'python':platform.python_version(),'font':'Microsoft YaHei','dpi':300,'source':'results/*.npz and csv generated by src/model.py','figures':[{'file':k,'alt':v} for k,v in alts.items()]}
dump(manifest,ROOT/'figures'/'图表溯源.json')
# contact sheet for visual QA
paths=sorted((ROOT/'figures').glob('图??_*.png'));thumbs=[]
for p in paths:
    im=Image.open(p).convert('RGB');im.thumbnail((520,330));canvas=Image.new('RGB',(540,365),'white');canvas.paste(im,((540-im.width)//2,5));ImageDraw.Draw(canvas).text((10,340),p.stem,fill='black');thumbs.append(canvas)
sheet=Image.new('RGB',(1620,365*5),'#ddd')
for i,im in enumerate(thumbs):sheet.paste(im,((i%3)*540,(i//3)*365))
sheet.save(ROOT/'figures'/'图表总览_仅供校验.jpg',quality=90)
print('figures',len(paths))
