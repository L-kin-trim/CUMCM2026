from pathlib import Path
here=Path(__file__).resolve().parent
s=(here.parent/'build_reference_paper.py').read_text(encoding='utf-8')
s=s.replace('WORK=HERE.parent','WORK=HERE.parent.parent')
s=s.replace("OUT=HERE/'微网购电策略论文_范例风格完善版.docx'","OUT=HERE/'微网购电策略论文_图文增强版.docx'")
def insert_before(anchor,content):
    global s
    assert s.count(anchor)==1,anchor
    s=s.replace(anchor,content+'\n'+anchor)
insert_before("h('5.1.3 储能状态与运行边界',3)","""fig(HERE/'新增图/01_微网能量流.png','微网能量流及储能双向调节',15.5)
p('能量流图将母线的供给与去向对应到平衡方程。储能同时具有吸收和释放电能两种运行方向，实际时段按状态选择其一；富余弃置不产生售电收入。')""")
insert_before("h('5.3.2 历史残差情景与日前目标函数',3)","""fig(HERE/'新增图/02_典型日预测.png','2025年6月21日的负载与光伏预测对比',15.5)
p('典型日曲线显示，预测能够刻画主要日内变化，但局部偏差仍然存在。负载与光伏偏差共同改变净负荷，因此购电优化还需考虑历史残差情景；单日图形仅作说明，整体精度以外样本误差表为准。')""")
insert_before("h('5.4 问题3的模型建立与求解',2)","""fig(HERE/'新增图/03_月度紧急购电.png','问题2与问题3策略D的月度紧急购电量',15.5)
p('月度统计将全年紧急购电分解到各月，用于观察风险在时间上的分布及预报更新后的变化。两组策略均按同一实际序列连续运行，图中差异反映预测输入、计划调整和储能状态传递的综合作用。')""")
insert_before("h('5.4.2 调整费用模型',3)","""fig(HERE/'新增图/04_滚动调整热力图.png','2025年6月21日各次预报触发的计划增减',15.5)
p('热力图中的红色表示相对上一有效计划增购，蓝色表示减购，灰色为更新时刻以前已经执行的区间。图中各次调整仅作用于未来时段，直观体现了已执行交易冻结的约束。')""")
insert_before("h('5.6 指定日期的调度结果',2)","""fig(HERE/'新增图/05_电价购电储能联动.png','2025年6月21日波动电价下的购电与储能联动',15.5)
p('图示对应当天价格曲线已知条件下的问题4-3策略D。共同时间轴展示价格变化、时段购电量与储电状态的联系；储电量虚线为上下边界。调度还受光伏、负载与调整费影响，不能仅凭价格高低判断某时段是否应购电。')""")
insert_before("h('第6章　模型评价与改进')","""fig(HERE/'新增图/06_敏感性对比.png','关键参数变化对24日库存校正费用的影响',15.5)
p('以零变化线为参照，左侧表示费用下降，右侧表示费用上升。该图与敏感性表使用相同的策略D和24日样本，便于比较效率、容量及结算参数的影响方向，不能据此代替全年重新求解。')""")
s=s.replace("'deliver.py','figures.py']","'deliver.py','figures.py','make_added_figures.py']")
s=s.replace("source=(SRC/fname).read_text(encoding='utf-8')","source=((HERE if fname=='make_added_figures.py' else SRC)/fname).read_text(encoding='utf-8')")
s=s.replace("['src/figures.py','计算结果图形生成']","['src/figures.py','原有计算结果图形生成'],['make_added_figures.py','本次新增6幅图及数据溯源']")
(here/'build_illustrated_paper.py').write_text(s,encoding='utf-8')
print('Builder ready')
