"""论文新增图：固定数据口径、中文字体、300 dpi；不使用示意数据冒充结果。"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
HERE=Path(__file__).resolve().parent.parent
R=HERE.parent/'审查与完善/07_复现代码与数据/results'
O=HERE/'图';O.mkdir(exist_ok=True)
plt.rcParams.update({'font.sans-serif':['SimSun','Microsoft YaHei'],'axes.unicode_minus':False,'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
B='#0072B2';C='#D55E00'
def save(fig,name):
    fig.savefig(O/(name+'.png'),dpi=300,bbox_inches='tight',facecolor='white');plt.close(fig)
def flow(name,labels,sub):
    fig,ax=plt.subplots(figsize=(6.3,2.15));ax.set(xlim=(0,10),ylim=(0,3));ax.axis('off')
    for i,(label,detail) in enumerate(zip(labels,sub)):
        x=.1+i*2.5
        ax.add_patch(FancyBboxPatch((x,.65),2.2,1.6,boxstyle='round,pad=.04',fc='#F5F8FA',ec=B,lw=1.2))
        ax.text(x+1.1,1.8,label,ha='center',va='center',fontsize=11)
        ax.text(x+1.1,1.2,detail,ha='center',va='center',fontsize=9,linespacing=1.5)
        if i<3:ax.annotate('',(x+2.47,1.45),(x+2.23,1.45),arrowprops=dict(arrowstyle='->',color='#333333',lw=1.2))
    save(fig,name)
flow('09_总体流程',['数据与信息','预测与情景','购电与储能','回放与检验'],['10分钟映射\n历史截止点','滚动训练\n整日残差','日前计划\n分时调整','连续传递库存\n四方面验证'])
flow('10_信息时序',['0时日前','6时更新','12时更新','18时更新'],['历史负载\n当次光伏预报','固定已执行量\n更新剩余18小时','固定已执行量\n更新剩余12小时','固定已执行量\n更新剩余6小时'])
data=np.load(R/'data.npz')
fig,axs=plt.subplots(1,2,figsize=(6.3,2.7),layout='constrained')
for ax,key,title in zip(axs,['L','PV'],['全年负载','全年光伏']):
    im=ax.imshow(data[key],aspect='auto',extent=(0,24,365,1),cmap='YlOrRd',vmin=0,vmax=max(data['L'].max(),data['PV'].max()))
    ax.set(xlabel='日内时刻 / h',ylabel='年内日序',title=title,xticks=[0,6,12,18,24])
fig.colorbar(im,ax=axs,label='功率 / kW',shrink=.9);save(fig,'11_全年数据热图')
fig,axs=plt.subplots(1,2,figsize=(6.3,2.7),layout='constrained')
e=np.load(HERE/'检验结果/误差数组.npz')['net_error'];actual=(data['L']-data['PV'])[31:];pred=actual+e
hb=axs[0].hexbin(actual.ravel(),pred.ravel(),gridsize=35,cmap='Blues',mincnt=1,bins='log')
lo=min(actual.min(),pred.min());hi=max(actual.max(),pred.max());axs[0].plot([lo,hi],[lo,hi],c=C,lw=1)
axs[0].set(xlabel='实际净负荷 / kW',ylabel='预测净负荷 / kW',title='外样本预测与实际')
axs[1].hist(e.ravel(),bins=50,color=B,alpha=.85);axs[1].axvline(0,c=C,lw=1)
axs[1].set(xlabel='预测减实际 / kW',ylabel='时段数',title='净负荷预测误差分布');save(fig,'12_误差诊断')
st=pd.read_csv(HERE/'检验结果/固定计划压力检验.csv')
fig,ax=plt.subplots(figsize=(6.3,2.5),layout='constrained');bar=ax.bar(np.arange(4),st.emergency_cost/10000,color=[B,C,C,C])
ax.bar_label(bar,fmt='%.2f',fontsize=9);ax.set(xticks=np.arange(4),xticklabels=st['case'],ylabel='紧急购电费 / 万元',ylim=(0,1700));save(fig,'13_压力检验')
gain=pd.read_csv(HERE/'检验结果/日费用配对差.csv');means=np.load(HERE/'检验结果/区块重采样.npz')['means']
fig,axs=plt.subplots(1,2,figsize=(6.3,2.5),layout='constrained')
axs[0].plot(np.arange(1,335),gain.gain.cumsum()/10000,c=B);axs[0].axhline(0,c='gray',lw=.7)
axs[0].set(xlabel='外样本日序',ylabel='累计库存校正节省 / 万元')
axs[1].hist(means,bins=35,color=B);ci=np.quantile(means,[.025,.975])
for v in ci:axs[1].axvline(v,c=C,ls='--')
axs[1].set(xlabel='日均节省 / 元',ylabel='重采样次数');save(fig,'14_配对比较')
df=pd.read_csv(R/'年度汇总.csv').set_index('model').loc[['q2','q3_D','q42','q43_D']]
fig,ax=plt.subplots(figsize=(6.3,2.5),layout='constrained');xx=np.arange(4)
ax.bar(xx,df.base/10000,label='计划费',color=B)
ax.bar(xx,df.emergency/10000,bottom=df.base/10000,label='紧急费',color=C)
# 调整费可能为负，用独立点表示，避免负堆叠误读。
ax.scatter(xx,df.total/10000,marker='D',c='black',s=25,label='含净调整费的总费',zorder=3)
ax.set(xticks=xx,xticklabels=['问题2','问题3 D','问题4-2','问题4-3 D'],ylabel='费用 / 万元');ax.legend(fontsize=8,ncol=3,loc='upper center',bbox_to_anchor=(.5,1.2));save(fig,'15_费用构成')
flow('16_检验框架',['灵敏度分析','稳健性检验','误差分析','对比验证'],['效率与容量\n结算与裕度','固定计划受扰动\n可行性和经济性','外样本净负荷\n偏差与尾部误差','独立求解与回读\n配对区块重采样'])
print('新增8幅图已生成')
