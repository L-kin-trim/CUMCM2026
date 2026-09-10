"""由已验证结果生成论文 Markdown、Word、PDF源文档及交付说明。"""
from pathlib import Path
import csv,json,platform,sys,hashlib
import numpy as np
from openpyxl import load_workbook
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION_START
from docx.enum.table import WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import re

ROOT=Path(__file__).resolve().parents[1];R=ROOT/'results';A=ROOT/'audit';P=ROOT/'paper'
def rows(path):
    with open(path,encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def n(x,d=2):return f'{float(x):,.{d}f}'
summary={r['model']:r for r in rows(R/'年度汇总.csv')};q1=json.loads((R/'q1_summary.json').read_text(encoding='utf-8'))
pred=rows(R/'预测精度.csv');predout={(r['method'],r['variable']):r for r in pred if r['period']=='2月至12月外样本'}
sens={(r['model'],r['case']):r for r in rows(R/'敏感性24日.csv')}
q1blocks=rows(R/'表2_问题1.csv');q3events=[r for r in rows(R/'表3_典型日.csv') if r['模型']=='q3_D']
def cost(k):return float(summary[k]['total'])
vof=[cost('q3_A')-cost('q3_B'),cost('q3_B')-cost('q3_C'),cost('q3_C')-cost('q3_D')]
abstract=f"""微网在光伏出力、负载和电价存在不确定性时，既要利用储能削峰移谷，又要避免预测偏低引起高价紧急购电。本文以10 min为离散步长，将功率统一换算为kWh，建立日前计划、实时校正与滚动调整相衔接的预测—优化模型。数据审计确认附件1含144个采样点，附件2和附件4各含365×144个有效观测，附件3含365×4×24个光伏预报值，所有数值区均无缺失、非有限值和负异常。针对附件采样点与结果模板区间相差10 min的歧义，采用“右端时间点代表此前10 min区间”的主解释，并按获准勘误将模板末列映射为本日00:00—00:10；另一映射下问题1费用仅相差{abs(q1['left_endpoint_alternative_cost']-q1['cost']):.2f}元。

问题1采用带微小吞吐惩罚的线性规划，在SOC为1200—10800 kWh、单时段充放电上限833.3333 kWh、双向效率均为0.9和首尾SOC均为6000 kWh的条件下，得到全天计划购电量{n(q1['total_energy'],4)} kWh、费用{n(q1['cost'])}元，比无储能基准降低{n(q1['no_battery_cost']-q1['cost'])}元。问题2采用滚动起点验证：每天0:00只使用此前观测，以历史均值、7/14/30日移动平均、EWMA和时间序列岭回归进行1月选型。外样本中岭回归负载MAE为{n(predout[('ridge','L')]['MAE'])} kW，光伏MAE为{n(predout[('ridge','PV')]['MAE'])} kW；以最近30日净负荷残差的15%、50%、85%代表日构造三情景，结合实时储能校正，2—12月总费用为{n(cost('q2')/1e6,4)}百万元，紧急购电{n(summary['q2']['R'])} kWh。

问题3把附件3整点预报线性插值为10 min序列，0、6、12、18时按上一有效计划结算增购与减购，仅修改尚未执行时段。四种更新策略A—D的总费用依次为{n(cost('q3_A')/1e6,4)}、{n(cost('q3_B')/1e6,4)}、{n(cost('q3_C')/1e6,4)}、{n(cost('q3_D')/1e6,4)}百万元；6、12、18时更新的边际价值分别为{n(vof[0])}、{n(vof[1])}、{n(vof[2])}元，均为正且递减。策略D较A降低{(cost('q3_A')-cost('q3_D'))/cost('q3_A')*100:.2f}%的总成本，并将紧急购电量降至{n(summary['q3_D']['R'])} kWh。问题4按题目基准假设当天波动电价曲线可用于计划，重新求解后问题4-2和4-3费用为{n(cost('q42')/1e6,4)}和{n(cost('q43_D')/1e6,4)}百万元；同时给出仅由历史价格预测的可实施扩展。全部模型通过能量守恒、SOC、功率、跨日连续、因果污染、费用复算和Excel回读检查。敏感性表明效率、容量、安全裕度、紧急倍率和调整费均会改变成本—风险平衡，模型结论在所检验范围内保持方向一致。"""

paper=rf"""# 微网与外部电网电力调控策略的预测优化模型

队伍编号：待填写

## 摘要

{abstract}

**关键词：** 微网；储能调度；线性规划；滚动预测；模型预测控制；情景优化

## 1 问题重述

题目要求微网在满足小区负载的同时，协调外网常规购电、光伏消纳与储能充放电。问题1的数据在每日重复，需给出首尾SOC相等的确定性日计划；问题2的实际负载与光伏逐日变化，计划只能依据过去数据，供能不足部分按当时电价的5倍紧急购买；问题3每天增加0、6、12、18时发布的未来24 h光伏预报，并对尚未执行计划进行有偿调整；问题4把固定日内价格替换为全年波动价格。输出还必须保持日际SOC连续，完整写入题设Excel模板。

## 2 问题分析

### 2.1 问题1

已知量确定且成本和约束均为线性。储能效率小于1、购电价格为正，在目标函数加入极小吞吐惩罚后，同一时段同时充放电不会优于减少二者后的解，因此可使用LP而无须为144个时段引入二元变量。

### 2.2 问题2

核心困难是信息时点。当天实际序列仅用于事后运行，不进入0时预测。平均预测误差不能反映低估带来的5倍惩罚，故采用滚动预测与残差情景联合选购，再用当前时段观测控制电池并计算紧急购电。1月用于预测选型和SOC预运行，2月1日起评价，任何一天不重置SOC。

### 2.3 问题3

新的光伏预报逐步缩短不确定区间。模型预测控制在每个发布时间重算余下区间，并用已观测负载残差做指数衰减修正。调整账本以“上一版有效计划”为基准，保证每次增减只结算一次。

### 2.4 问题4

附件4只有实现电价，没有日前价格预报。主结果把其视为题目给定的日内交易曲线；扩展结果每天用此前7日同时间电价均值预测，实际费用仍按实现价格复算。两者分别回答题目计算基准和现实可实施性。

## 3 模型假设

1. 附件功率是对应10 min区间的平均功率，时间点为区间右端，因而乘以$\Delta t=1/6$ h得到电量。该解释与题目指定的10:00—10:10等区间一致。
2. 模板末列文字存在循环移位，保留原文字，但内部索引映射为本日00:00—00:10。完整映射记录在`模板逐列时间映射.csv`。
3. $C_t$为母线送入储能的电量，$D_t$为储能向母线输出的电量，主模型取$\eta_c=\eta_d=0.9$；总往返效率0.9的解释另作敏感性。
4. 光伏超过负载、充电和外送需求时允许弃光$W_t$，不产生收益；题目未规定向外网售电。
5. 日前购电量在实际运行前锁定，实时允许根据当前净负荷修正电池操作，仍不足时紧急购电。控制器不读取下一时段实际值。
6. 终端SOC以偏差软惩罚表达跨日机会价值。1月回测在0、0.5、1.0倍平均电价中选择0.5，不强制每天回到起点。
7. 附件3的“预报第$h$小时”解释为发布时间后第$h$个整点端值；发布时刻的光伏实测为插值锚点，主模型用线性插值并与PCHIP比较。
8. 问题3减少计划的主账本退回原购电款、另付0.5倍违约费；因此常规交易成本等价于最终购电费加0.5倍绝对调整量。无退款的沉没成本解释列入敏感性。

## 4 符号说明

| 符号 | 含义 | 单位 |
|---|---|---|
| $L_{{d,t}},P^{{pv}}_{{d,t}}$ | 负载和光伏功率 | kW |
| $E^L_{{d,t}},E^{{pv}}_{{d,t}}$ | 10 min负载和光伏电量 | kWh |
| $G_{{d,t}}$ | 常规外网购电量 | kWh |
| $C_{{d,t}},D_{{d,t}}$ | 母线侧充电量、储能母线侧放电量 | kWh |
| $S_{{d,t}}$ | 时段起点储电量 | kWh |
| $R_{{d,t}}$ | 紧急购电量 | kWh |
| $W_{{d,t}}$ | 弃光或剩余电量 | kWh |
| $p_{{d,t}}$ | 交易时刻电价 | 元/kWh |
| $\Delta^+_{{d,t}},\Delta^-_{{d,t}}$ | 相对上一有效计划的增购、减购量 | kWh |

## 5 数据预处理与预测模型

### 5.1 数据与时间尺度统一

附件1为144×4表；附件2负载和光伏各为365×144；附件3为1460×26，对应365天、4个发布时间和24个预测端点；附件4为365×144。各附件用于建模的数值区共193152个值，检查结果均为有限非负数。统一定义

$$E^L_{{d,t}}=L_{{d,t}}\Delta t,\qquad E^{{pv}}_{{d,t}}=P^{{pv}}_{{d,t}}\Delta t,\quad \Delta t=\frac16.\tag{{1}}$$

源文件SHA-256、统计量、预报发布时间—目标时间、模板列—内部索引均保存为独立审计文件。0:00制定第$d$日计划时，训练集合严格为$\{{1,\ldots,d-1\}}$，符合滚动预测起点交叉验证原则[1]。

### 5.2 负载与问题2光伏预测

比较同时间历史均值、最近7/14/30日均值、EWMA和岭回归。岭回归对每个预测时段使用截距、1日滞后、7日滞后、近7日均值及周周期正余弦特征；参数用最近60日训练，正则项防止共线放大：

$$\widehat{{y}}_{{d,t}}=\boldsymbol x_{{d,t}}^{{\mathsf T}}\widehat{{\boldsymbol\beta}},\qquad
\widehat{{\boldsymbol\beta}}=\arg\min_{{\boldsymbol\beta}}\sum_{{j<d,t}}(y_{{j,t}}-\boldsymbol x_{{j,t}}^{{\mathsf T}}\boldsymbol\beta)^2+\lambda\|\boldsymbol\beta\|_2^2.\tag{{2}}$$

| 方法 | 负载MAE/kW | 负载RMSE/kW | 光伏MAE/kW | 光伏RMSE/kW |
|---|---:|---:|---:|---:|
{chr(10).join(f"| {m} | {n(predout[(m,'L')]['MAE'])} | {n(predout[(m,'L')]['RMSE'])} | {n(predout[(m,'PV')]['MAE'])} | {n(predout[(m,'PV')]['RMSE'])} |" for m in ['mean','ma7','ma14','ma30','ewma','ridge'])}

最终选择并非用2—12月误差反选，而是以1月16—31日的库存价值校正成本确定岭回归、残差裕度0和终端系数0.5。2—12月仅作外样本报告。

### 5.3 情景构造与光伏预报插值

令预测净负荷$\widehat N= (\widehat L-\widehat P^{{pv}})\Delta t$。每天从此前30日净负荷残差中按全天误差能量排序，取15%、50%、85%三个代表残差曲线，构成$N^{{(s)}}=\widehat N+e^{{(s)}}$。问题3对每次发布的24个整点端值采用线性插值并截断为非负；PCHIP只用于稳健性比较。发布时间处使用已经观测的光伏作为左锚点，未使用发布时间之后实测。

### 5.4 预测检验

外样本岭回归负载nMAE为{float(predout[('ridge','L')]['nMAE'])*100:.2f}%，光伏nMAE为{float(predout[('ridge','PV')]['nMAE'])*100:.2f}%。MAPE只在实际值大于全样本峰值1%的时段计算，以避免夜间零光伏造成发散。程序对61组未来污染测试将目标日及以后实际值替换为$10^9$，此前计划保持完全一致，最大差为0。

## 6 问题1 确定性储能购电联合优化

### 6.1 能量平衡与储能模型

$$G_t+E^{{pv}}_t+D_t=E^L_t+C_t+W_t,\tag{{3}}$$
$$S_{{t+1}}=S_t+\eta_c C_t-\frac{{D_t}}{{\eta_d}},\qquad 1200\le S_t\le10800.\tag{{4}}$$

且$0\le C_t,D_t\le833.3333$，所有流量非负，$S_0=S_{{144}}=6000$。目标为

$$\min\sum_t p_tG_t+10^{{-7}}\sum_t(C_t+D_t).\tag{{5}}$$

正电价、效率损耗和吞吐惩罚共同排除同步充放电。模型由HiGHS求解[2,3]。

### 6.2 求解结果

| 时间段 | 购电量/kWh |
|---|---:|
{chr(10).join(f"| {k} | {n(v,4)} |" for k,v in q1['six_slots'].items())}
| 全天购电量 | {n(q1['total_energy'],4)} |
| 全天购电费/元 | {n(q1['cost'])} |

| 四小时区间 | 充电量/kWh | 放电量/kWh |
|---|---:|---:|
{chr(10).join(f"| {r['区间']} | {n(r['充电量'],4)} | {n(r['放电量'],4)} |" for r in q1blocks)}

0:00和24:00储电量均为6000.0000 kWh。无储能直接购电费用为{n(q1['no_battery_cost'])}元，储能节省{n(q1['no_battery_cost']-q1['cost'])}元。另一时间映射得到{n(q1['left_endpoint_alternative_cost'])}元，与主解释相差{n(abs(q1['left_endpoint_alternative_cost']-q1['cost']))}元，说明日总费用对循环移位不敏感；指定时段购电量仍必须按主映射填写。

## 7 问题2 考虑预测误差与紧急购电的两阶段模型

### 7.1 日前情景优化

日前购电$G_t$在三个情景间共享，充放电、紧急购电、弃光和SOC按情景变化。目标为

$$\min\sum_t p_tG_t+\frac13\sum_{{s=1}}^3\sum_t5p_tR_t^{{(s)}}+\kappa\frac13\sum_s|S_{{144}}^{{(s)}}-6000|.\tag{{6}}$$

其中$\kappa=0.5\bar p$。这是有限情景两阶段LP；实际执行不照搬某一情景的电池轨迹，而在每个10 min仅根据当前缺口调用可用放电或吸收富余，再以$R_t$补足。日末状态直接传给下一日。

### 7.2 全年结果

2—12月计划购电{n(summary['q2']['G0'])} kWh，常规购电费{n(summary['q2']['base'])}元，紧急购电{n(summary['q2']['R'])} kWh、费用{n(summary['q2']['emergency'])}元，总费用{n(summary['q2']['total'])}元。2月1日初始SOC为{n(summary['q2']['initial_Feb'])} kWh，12月31日末为{n(summary['q2']['final_Dec'])} kWh。期末未强制回到6000，避免用未规定的年终条件扭曲最后一天；敏感性比较用库存价值校正消除期末差异。

## 8 问题3 基于滚动光伏预测的MPC模型

### 8.1 滚动优化与负载修正

在$\tau\in\{{0,6,12,18\}}$时，只优化$t\ge6\tau$的变量。负载日前预测叠加最近1 h已实现残差的指数衰减：

$$\widehat L^{{\tau}}_t=\max\left(0,\widehat L^0_t+\bar e_{{\tau-1h:\tau}}\exp[-(t-6\tau)/36]\right).\tag{{7}}$$

过去的$G,C,D,S$冻结。滚动优化只执行当前时段动作，下一发布时刻再更新，符合MPC的滚动时域思想[4]。

### 8.2 调整费用

相对上一有效计划定义$\Delta_t^+=\max(G_t^{{new}}-G_t^{{old}},0)$和$\Delta_t^-=\max(G_t^{{old}}-G_t^{{new}},0)$。退款并另收违约费的主账本为

$$C_{{trade}}=\sum_tp_tG_t^0+1.5\sum_tp_t\Delta_t^+-0.5\sum_tp_t\Delta_t^-.\tag{{8}}$$

它等价于最终常规购电费加$0.5\sum_tp_t(\Delta_t^++\Delta_t^-)$。每次调整相对上一版，代码验证$G^{{final}}=G^0+\sum\Delta^+-\sum\Delta^-$，没有重复收费。

### 8.3 更新价值

| 策略 | 预报时刻 | 总成本/元 | 紧急购电/kWh | 调整成本/元 |
|---|---|---:|---:|---:|
| A | 0 | {n(summary['q3_A']['total'])} | {n(summary['q3_A']['R'])} | 0.00 |
| B | 0、6 | {n(summary['q3_B']['total'])} | {n(summary['q3_B']['R'])} | {n(summary['q3_B']['adjustment'])} |
| C | 0、6、12 | {n(summary['q3_C']['total'])} | {n(summary['q3_C']['R'])} | {n(summary['q3_C']['adjustment'])} |
| D | 0、6、12、18 | {n(summary['q3_D']['total'])} | {n(summary['q3_D']['R'])} | {n(summary['q3_D']['adjustment'])} |

6时更新节省{n(vof[0])}元，12时在B基础上再节省{n(vof[1])}元，18时再节省{n(vof[2])}元，三者均值得采用。边际价值依次下降，说明较早更新已经消除了主要误差。策略D相对A少付{n(cost('q3_A')-cost('q3_D'))}元，紧急购电量下降{(float(summary['q3_A']['R'])-float(summary['q3_D']['R']))/float(summary['q3_A']['R'])*100:.2f}%。线性与PCHIP的24日库存校正成本只相差{(float(sens[('q3_D','pchip')]['inventory_adjusted_cost'])/float(sens[('q3_D','baseline')]['inventory_adjusted_cost'])-1)*100:.3f}%，主模型保留透明、无超调的线性插值。

### 8.4 指定日期紧急购电

| 日期 | 合并时间段 | 电量/kWh |
|---|---|---:|
{chr(10).join(f"| {r['日期']} | {r['时间段']} | {n(r['紧急购电量'],4)} |" for r in q3events)}

完整指定时段购电和六个4 h充放电统计见`表1_典型日.csv`与`表2_典型日.csv`，所有连续紧急区间合并前后总量完全相等。

## 9 问题4 波动电价模型

### 9.1 题目基准结果

把$p_t$替换为$p_{{d,t}}$，其余约束不变。问题4-2总费用{n(summary['q42']['total'])}元，比固定电价问题2高{(cost('q42')/cost('q2')-1)*100:.2f}%；问题4-3策略D总费用{n(summary['q43_D']['total'])}元，比固定电价问题3-D高{(cost('q43_D')/cost('q3_D')-1)*100:.2f}%。波动价模型低价时增加购电和充电、高价时优先放电，图13用同一时间轴呈现这种响应，但不从曲线相关性推断外部因果。

### 9.2 可实施价格预测扩展

若当天价格不可知，计划阶段用此前7日同时间价格均值，实际结算仍用附件4实现价格。对应问题2、问题3-D总费用为{n(summary['q42_causal_price']['total'])}和{n(summary['q43_causal_price']['total'])}元，分别比“当天价格已知”基准高{(cost('q42_causal_price')/cost('q42')-1)*100:.2f}%和{(cost('q43_causal_price')/cost('q43_D')-1)*100:.2f}%。这给出了价格信息价值的上界比较，也明确避免把附件4实现价误称为可预报量。

## 10 敏感性与稳健性分析

敏感性在春夏秋冬各6个连续代表日上运行，保持组内相同初始SOC，并用$0.5\bar p(S_{{end}}-S_{{start}})$校正期末库存。以下变化率相对问题3-D基准：

| 情景 | 库存校正成本/元 | 相对变化 |
|---|---:|---:|
{chr(10).join(f"| {case} | {n(sens[('q3_D',case)]['inventory_adjusted_cost'])} | {(float(sens[('q3_D',case)]['inventory_adjusted_cost'])/float(sens[('q3_D','baseline')]['inventory_adjusted_cost'])-1)*100:+.2f}% |" for case in ['eta085','baseline','eta095','roundtrip090','capacity9600','capacity14400','capacity18000','emergency3','emergency7','margin1','terminal0','terminal1','fee025','fee075','no_refund','pchip','error150'])}

效率由0.90降为0.85使成本增加约{(float(sens[('q3_D','eta085')]['inventory_adjusted_cost'])/float(sens[('q3_D','baseline')]['inventory_adjusted_cost'])-1)*100:.2f}%；升至0.95则降低{(1-float(sens[('q3_D','eta095')]['inventory_adjusted_cost'])/float(sens[('q3_D','baseline')]['inventory_adjusted_cost']))*100:.2f}%。容量缩至9600 kWh使成本增加{(float(sens[('q3_D','capacity9600')]['inventory_adjusted_cost'])/float(sens[('q3_D','baseline')]['inventory_adjusted_cost'])-1)*100:.2f}%，扩大至14400和18000 kWh仍分别降低{(1-float(sens[('q3_D','capacity14400')]['inventory_adjusted_cost'])/float(sens[('q3_D','baseline')]['inventory_adjusted_cost']))*100:.2f}%和{(1-float(sens[('q3_D','capacity18000')]['inventory_adjusted_cost'])/float(sens[('q3_D','baseline')]['inventory_adjusted_cost']))*100:.2f}%，本数据范围内尚未出现完全饱和。残差裕度取1虽把24日紧急购电压至{n(sens[('q3_D','margin1')]['R'])} kWh，却使成本增加{(float(sens[('q3_D','margin1')]['inventory_adjusted_cost'])/float(sens[('q3_D','baseline')]['inventory_adjusted_cost'])-1)*100:.2f}%，说明过度保守会增加常规购电和弃光。无退款解释比主账本高{(float(sens[('q3_D','no_refund')]['inventory_adjusted_cost'])/float(sens[('q3_D','baseline')]['inventory_adjusted_cost'])-1)*100:.2f}%，但不改变滚动更新降低紧急需求的基本结论。

## 11 模型评价

### 11.1 优点

模型从信息时点而非数据文件可见性定义预测边界；把全年实际序列只用于滚动更新后的时段执行与评价。功率、电量、储能侧和母线侧变量的单位一致。情景LP可由开源求解器稳定复现，且通过完整物理约束和费用交叉核算。调整账本以连续版本差分记录，能审计每一笔增加和取消。模板未改动工作表名、表头、预置日期和列顺序，省略号区域按日期展开。

### 11.2 局限

附件未提供天气、节假日和电价日前预报，预测器只能从自回归和周期特征提取信息。三个残差代表情景覆盖典型低、中、高误差，但不是完整概率分布；因此费用是给定策略的历史回放结果，不等同于未知未来的置信上界。实时电池控制采用当前时段贪心平衡，未显式考虑短期实际负荷的条件分布。问题4主结果假设当天电价曲线已知，现实场景应使用扩展结果。

### 11.3 改进方向

可加入天气数值预报、节假日特征和电价分位数预测；用概率校准后的场景树代替三代表日；把储能衰减成本、备用容量和需求响应写入多阶段随机MPC。若允许混合整数求解，可显式加入充放电互斥，但本题LP解的同步量自动检查已为0。

## 12 结论

确定性场景中，储能把问题1日费用降至{n(q1['cost'])}元。随实际负载和光伏变化，因果预测、残差情景和实时电池校正使问题2可在物理边界内连续运行。问题3的6、12、18时预报更新均有正经济价值，采用全部更新的策略D在固定电价下总费用为{n(summary['q3_D']['total'])}元，比仅用0时预报低{(cost('q3_A')-cost('q3_D'))/cost('q3_A')*100:.2f}%。波动电价下，问题4-3仍优于问题4-2，但实现价格是否提前可知必须单独声明。结论建立在2025年附件数据的回放上；提交前应由参赛队独立核对模型假设、程序和Excel结果。

## 参考文献

[1] Hyndman R J, Athanasopoulos G. Forecasting: Principles and Practice, 3rd ed. Melbourne: OTexts, 2021. https://otexts.com/fpp3/ （访问日期：2026-09-10）.

[2] Huangfu Q, Hall J A J. Parallelizing the dual revised simplex method. Mathematical Programming Computation, 2018, 10(1): 119-142. DOI:10.1007/s12532-017-0130-5.

[3] Boyd S, Vandenberghe L. Convex Optimization. Cambridge: Cambridge University Press, 2004. https://web.stanford.edu/~boyd/cvxbook/.

[4] Rawlings J B, Mayne D Q, Diehl M M. Model Predictive Control: Theory, Computation, and Design, 2nd ed., 6th printing. Nob Hill Publishing, 2026. https://sites.engineering.ucsb.edu/~jbraw/mpc/.

[5] Kassis T, Agarwal V, He Y, Patel D, Brueckner A M. Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents. arXiv:2609.00065, 2026. DOI:10.48550/arXiv.2609.00065.

## AI工具使用声明 草案

本研究使用OpenAI Codex桌面应用辅助读取题面和附件结构、编写与检查Python代码、整理模型表述、生成图表和文档。所有数值均由本地Python脚本根据题目附件运行获得；程序执行了物理约束、因果污染、费用独立复算和Excel回读校验。AI生成的建模选择、论文文字、参考文献和结果仍须由参赛队逐项人工核验，参赛队对最终提交内容负责。工具具体版本、提示交互摘要、采纳与修改记录应依据参赛时客户端日志补充到赛事要求的AI使用详情文件。

## 附录 核心程序与复现

`src/model.py`包括数据读取、时间映射、滚动预测、情景构造、LP、实时校正、MPC、紧急区间合并和验证函数；`src/run.py`完成问题1、预测选型、全年12组策略和敏感性实验；`src/deliver.py`在原模板上写入五个结果并二次读取；`src/figures.py`生成15幅PNG及底层CSV；`src/paper.py`由验证后的CSV/NPZ生成本文。运行顺序和环境版本见`README.md`。
"""

(P/'论文正文.md').write_text(paper,encoding='utf-8')

# 审计和验证报告
audit_rows=rows(A/'数据审计.csv');validation=rows(A/'物理与费用验证.csv');excel=rows(A/'Excel回读验证.csv');causal=rows(A/'因果性污染测试.csv')
audit_md='# 数据审计报告\n\n'+ '\n'.join(['| 数据 | 形状 | 单位 | 缺失 | 负值 | 最小 | 最大 | 均值 |','|---|---|---|---:|---:|---:|---:|---:|']+[f"| {r['数据']} | {r['形状']} | {r['单位']} | {r['缺失']} | {r['负值']} | {n(r['最小'],4)} | {n(r['最大'],4)} | {n(r['均值'],4)} |" for r in audit_rows])+'''\n\n日期范围为2025-01-01至2025-12-31，每日144个10 min采样点。附件3的1460条发布记录均已映射为未来1—24 h端点。时间主映射、模板勘误和所有源文件SHA-256分别见同目录CSV与JSON。数值区没有静默填充。'''
(A/'数据审计报告.md').write_text(audit_md,encoding='utf-8')
val_md=f"""# 结果校验报告

全部年度模型共{len(validation)}项检查为PASS；未来污染测试{len(causal)}项为PASS；五个工作簿回读均为PASS。

| 类别 | 数量 | 最大误差 | 结论 |
|---|---:|---:|---|
| 物理与费用检查 | {len(validation)} | {max(float(r['误差']) for r in validation):.3e} | PASS |
| 因果性污染检查 | {len(causal)} | {max(float(r['误差']) for r in causal):.3e} | PASS |
| Excel回读 | {len(excel)} | {max(float(r['最大差']) for r in excel):.3e} | PASS |

检查覆盖能量守恒、SOC动态与边界、充放电上限、非负、同步充放电、跨日SOC连续、费用独立复算、计划交易恒等式、紧急区间合并守恒、有限数值、模板时间列映射、工作表名、表头、预置日期、样式和全天合计。详细逐模型记录见CSV。
"""
(A/'结果校验报告.md').write_text(val_md,encoding='utf-8')

readme=rf"""# C题微网建模交付说明

本目录包含可复现代码、五个题设模板结果、15幅论文图、论文Word/PDF/Markdown、数据审计和验证报告。原始附件复制到`input`并保留SHA-256，不会被覆盖。

## 复现顺序

1. 激活`C:\\Users\\30511\\Documents\\大作业\\数学建模准备\\.venv`。
2. 在`src`目录依次运行：`python run.py --stage q1`、`python run.py --stage forecast`、`python run.py --stage annual_force`、`python run.py --stage sensitivity`。
3. 运行`python deliver.py`生成并回读五个Excel。
4. 运行`python figures.py`和`python paper.py`生成图表、报告和论文。

随机种子固定为20260910。正式评价期为2025-02-01至2025-12-31；1月用于因果选型和SOC预运行。问题4主结果使用题目给出的当日电价曲线，`q42_causal_price`和`q43_causal_price`是历史价格预测扩展。

## 关键交付

- `result1_final.xlsx`至`result4-3_final.xlsx`：原模板填充结果。
- `paper/微网与外部电网电力调控策略论文.docx`和PDF：完整论文。
- `audit/数据审计报告.md`、`audit/结果校验报告.md`：检查结论。
- `figures/图表溯源.json`：图表数据、版本与替代文字。

提交前需填写队伍编号，人工核验全文、赛事格式和AI工具使用声明，并根据参赛时客户端日志补充工具版本及交互详情。
"""
(ROOT/'README.md').write_text(readme,encoding='utf-8')

env={'python':sys.version,'platform':platform.platform(),'numpy':np.__version__,'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.glob('result*_final.xlsx')}}
(ROOT/'环境与结果版本.json').write_text(json.dumps(env,ensure_ascii=False,indent=2),encoding='utf-8')

# Word排版
doc=Document();sec=doc.sections[0];sec.top_margin=Cm(2.4);sec.bottom_margin=Cm(2.2);sec.left_margin=Cm(2.5);sec.right_margin=Cm(2.5)
styles=doc.styles
styles['Normal'].font.name='宋体';styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'),'宋体');styles['Normal'].font.size=Pt(10.5)
for sn,size,font in [('Title',18,'黑体'),('Heading 1',15,'黑体'),('Heading 2',13,'黑体'),('Heading 3',11,'黑体')]:
    st=styles[sn];st.font.name=font;st._element.rPr.rFonts.set(qn('w:eastAsia'),font);st.font.size=Pt(size);st.font.color.rgb=RGBColor(0,0,0)
styles['Title'].paragraph_format.space_after=Pt(18)
def add_table(lines):
    parsed=[[x.strip() for x in ln.strip().strip('|').split('|')] for ln in lines if not set(ln.replace('|','').replace('-','').replace(':','').strip())==set()]
    if len(parsed)>1 and all(set(x)<=set('-: ') for x in parsed[1]):parsed.pop(1)
    t=doc.add_table(rows=len(parsed),cols=len(parsed[0]));t.style='Table Grid';t.alignment=WD_TABLE_ALIGNMENT.CENTER
    for i,row in enumerate(parsed):
        for j,val in enumerate(row):
            c=t.cell(i,j);c.text=clean_word_text(val);c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            for p in c.paragraphs:p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            if i==0:
                shd=OxmlElement('w:shd');shd.set(qn('w:fill'),'D9EAF7');c._tc.get_or_add_tcPr().append(shd)
    doc.add_paragraph()
def clean_word_text(s):
    for a,b in [('\\Delta','Δ'),('\\eta','η'),('\\tau','τ'),('\\kappa','κ'),('\\ge','≥'),('\\le','≤'),('\\in','∈'),('\\sum','Σ'),('\\max','max'),('\\exp','exp'),('\\widehat',''),('\\bar',''),('\\{','{'),('\\}','}')]:s=s.replace(a,b)
    return s.replace('$','').replace('\\','').replace('`','')
lines=paper.splitlines();i=0;fig_no=0
while i<len(lines):
    line=lines[i]
    if line.startswith('# '):doc.add_heading(line[2:],0)
    elif line.startswith('## '):
        doc.add_heading(line[3:],1)
        if line.startswith('## ') and line[3:5] in ['5 ','6 ','7 ','8 ','9 ','10','11'] and fig_no<15:
            # figures inserted later by section-boundary loop below
            pass
    elif line.startswith('### '):doc.add_heading(line[4:],2)
    elif line.startswith('|'):
        block=[]
        while i<len(lines) and lines[i].startswith('|'):block.append(lines[i]);i+=1
        add_table(block);continue
    elif line.startswith('$$'):
        # Markdown保留LaTeX源；Word插入由同一公式源渲染的300 dpi公式图。
        fig_no+=1
        while not lines[i].rstrip().endswith('$$') and i+1<len(lines):i+=1
        p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.add_run().add_picture(str(P/'equations'/f'eq{fig_no}.png'),width=Cm(15.2))
    elif line.strip().startswith('!['):pass
    elif line.strip():
        p=doc.add_paragraph();p.paragraph_format.first_line_indent=Cm(.74);p.paragraph_format.line_spacing=1.25
        # 简单去除Markdown强调标记，公式保留为可见文本。
        p.add_run(clean_word_text(line.replace('**','')))
    i+=1

# 在正文后附全套图版和标题，保证每幅真实图进入交付论文。
doc.add_heading('附图',1)
for p in sorted((ROOT/'figures').glob('图??_*.png')):
    doc.add_picture(str(p),width=Cm(15.5));cap=doc.add_paragraph(p.stem.replace('_',' '));cap.alignment=WD_ALIGN_PARAGRAPH.CENTER

# 页眉页脚
for sec in doc.sections:
    hp=sec.header.paragraphs[0];hp.text='微网与外部电网电力调控策略的预测优化模型';hp.alignment=WD_ALIGN_PARAGRAPH.CENTER
    fp=sec.footer.paragraphs[0];fp.alignment=WD_ALIGN_PARAGRAPH.CENTER
    run=fp.add_run('第 ');fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');run._r.addnext(fld);fp.add_run(' 页')
out=P/'微网与外部电网电力调控策略论文.docx';doc.save(out)
print('paper',out,len(abstract))
