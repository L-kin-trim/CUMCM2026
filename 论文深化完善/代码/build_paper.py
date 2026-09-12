"""在前版内容上深化；编号为SEQ域，引用为REF域；LaTeX转为Word可编辑数学。"""
from pathlib import Path
import re,json
BASE=Path(__file__).resolve().parent.parent
old=BASE.parent/'论文范例对齐修订/图文增强版/build_illustrated_paper.py'
s=old.read_text(encoding='utf-8')
s=s.replace('HERE=Path(__file__).resolve().parent','HERE=Path(__file__).resolve().parent.parent').replace('WORK=HERE.parent.parent','WORK=HERE.parent')
s=s.replace("HERE/'新增图/","WORK/'论文范例对齐修订/图文增强版/新增图/")
# 保持12pt宋体及原章节风格；适度收紧行距，为检验和图形留出正文页数。
s=s.replace('Pt(23.4)','Pt(21)').replace('Pt(16);pp.paragraph_format.keep_with_next','Pt(13);pp.paragraph_format.keep_with_next')
s=s.replace("rr.font.size=Pt(size)","rr.font.size=Pt(min(size,10))")
start=s.index('def eq(tex):');end=s.index('\ndef caption(',start)
s=s[:start]+'''def bookmark(pp,name,callback):
    ident=str(len(doc.element.xpath('//w:bookmarkStart'))+1)
    b=OxmlElement('w:bookmarkStart');b.set(qn('w:id'),ident);b.set(qn('w:name'),name);pp._p.append(b)
    callback()
    b=OxmlElement('w:bookmarkEnd');b.set(qn('w:id'),ident);pp._p.append(b)
def field(pp,instruction,value):
    ff=OxmlElement('w:fldSimple');ff.set(qn('w:instr'),instruction)
    rr=OxmlElement('w:r');tt=OxmlElement('w:t');tt.text=str(value);rr.append(tt);ff.append(rr);pp._p.append(ff)
def ref(pp,name,value):field(pp,'REF '+name+' \\\\h',value)
def eq(tex):
    global n_eq
    n_eq+=1;notes.append('$$\\n'+tex+'\\n$$')
    # 左右留白对称，中央数学对象居中，自动编号位于最右单元格。
    tb=doc.add_table(rows=1,cols=3);tb.autofit=False
    for col,width in zip(tb.columns,[.8,14.4,.8]):col.width=Cm(width)
    for cell,width in zip(tb.rows[0].cells,[.8,14.4,.8]):
        cell.width=Cm(width);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
        cp=cell.paragraphs[0];cp.paragraph_format.first_line_indent=Pt(0);cp.paragraph_format.line_spacing=1
        cp.paragraph_format.space_before=Pt(4);cp.paragraph_format.space_after=Pt(4)
        tc=cell._tc.get_or_add_tcPr();bb=OxmlElement('w:tcBorders')
        for edge in ['top','bottom','left','right']:
            ed=OxmlElement('w:'+edge);ed.set(qn('w:val'),'nil');bb.append(ed)
        tc.append(bb)
        mar=OxmlElement('w:tcMar')
        for edge in ['left','right']:
            ed=OxmlElement('w:'+edge);ed.set(qn('w:w'),'0');ed.set(qn('w:type'),'dxa');mar.append(ed)
        tc.append(mar)
    cp=tb.cell(0,1).paragraphs[0];cp.alignment=WD_ALIGN_PARAGRAPH.CENTER
    mm=math(tex,True)
    if mm.tag==qn('m:oMathPara'):
        pr=mm.find(qn('m:oMathParaPr'))
        if pr is None:pr=OxmlElement('m:oMathParaPr');mm.insert(0,pr)
        jc=OxmlElement('m:jc');jc.set(qn('m:val'),'center');pr.append(jc)
    cp._p.append(mm)
    np=tb.cell(0,2).paragraphs[0];np.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    np.add_run('(');bookmark(np,'eq'+str(n_eq),lambda:field(np,'SEQ Equation \\\\* ARABIC',n_eq));np.add_run(')')
    for rr in np.runs:rr.font.size=Pt(10)
    tr=tb.rows[0]._tr.get_or_add_trPr();tr.append(OxmlElement('w:cantSplit'))
    return cp
''' + s[end:]
# 图编号自动化，并在紧接图的解释段中加入可点击交叉引用。
s=s.replace("pp.add_run().add_picture(str(path),width=Cm(width));caption(f'图5-{n_fig} {title}',False)","""pp.add_run().add_picture(str(path),width=Cm(width))
    cp=caption('',False);cp.add_run('图');bookmark(cp,'fig'+str(n_fig),lambda:field(cp,'SEQ Figure \\\\* ARABIC',n_fig));cp.add_run(' '+title)
    xp=p('',False);xp.paragraph_format.space_after=Pt(0);xp.paragraph_format.line_spacing=Pt(15)
    xp.add_run('图');ref(xp,'fig'+str(n_fig),n_fig);xp.add_run('给出'+title+'。')
    for rr in xp.runs:rr.font.size=Pt(10)
""")
# 删去旧图重复解释段首句，避免增加机械的图注复述；新交叉引用后仍保留实质解释。
s=s.replace("h('第3章　符号说明')","fig(HERE/'图/09_总体流程.png','四个问题的建模与验证流程',15)\nh('第3章　符号说明')")
s=s.replace("h('5.1.2 能量平衡模型',3)","fig(HERE/'图/11_全年数据热图.png','负载与光伏的全年日内分布',15)\nh('5.1.2 能量平衡模型',3)")
s=s.replace("h('5.4.1 分时预报更新与剩余时域',3)","fig(HERE/'图/10_信息时序.png','各预报时刻可调整的剩余时域',15)\nh('5.4.1 分时预报更新与剩余时域',3)")
s=s.replace("h('5.6 指定日期的调度结果',2)","fig(HERE/'图/15_费用构成.png','固定与波动电价下的费用构成',15)\nh('5.6 指定日期的调度结果',2)")
# 四方面检验：保留原灵敏度，重新组织其余内容。
a=s.index("h('5.7 模型检验与敏感性分析',2)");b=s.index("h('5.7.2 关键参数敏感性分析',3)",a)
s=s[:a]+"""h('5.7 模型检验',2)
p('检验分为灵敏度、稳健性、误差和对比验证四个方面。灵敏度改变模型参数，稳健性考察已定计划在不利输入下的表现，误差分析评价预测偏离程度，对比验证核对求解正确性及策略收益。四类检验使用不同证据，避免重复解释同一指标。')
fig(HERE/'图/16_检验框架.png','四方面模型检验框架',15)
h('5.7.1 灵敏度分析',3)
"""+s[b+len("h('5.7.2 关键参数敏感性分析',3)"):]
a=s.index("h('第6章　模型评价与改进')")
more=r'''
h('5.7.2 稳健性检验',3)
p('将问题3策略D的334天常规购电轨迹固定，保持2月初实际库存，分别施加负载增加5%、光伏减少10%及二者同时发生的持续扰动。全过程重新执行电池控制和紧急补购，日末库存连续传递；未来观测不用于改写计划。本试验衡量既定计划的抗扰能力，不能解释为允许重新预测和调度后的最优费用。')
st=checks['stress']
tab('固定计划的持续扰动检验',['扰动情形','紧急电量 / 万kWh','紧急费用 / 万元'],[[r['case'],f(r['emergency_kwh']/10000),f(r['emergency_cost']/10000)] for r in st],[6,5,5])
fig(HERE/'图/13_压力检验.png','固定常规购电计划在持续不利扰动下的代价',15)
p('四种情形的储电量均保持在1200—10800 kWh，平衡误差不超过1.14×10⁻¹³ kWh。联合扰动使紧急费用由14.48万元增加至1470.09万元，表明供电可行性具有保障，但既定计划的经济稳健性不足。该保障依赖题目未设外网购电上限；实际系统若存在外网限额，必须另设负荷损失约束和应急机制。')
p('与此不同，灵敏度实验中的残差裕度增加和不退款情形会重新优化计划，检验的是模型决策对参数变化的响应。两类试验的决策是否允许调整不同，费用不能混合排序。')
h('5.7.3 误差分析',3)
p('以2月至12月共48096个10分钟时段为外样本，对岭回归的净负荷功率预测计算误差。误差定义为预测减实际，正值意味着计划输入偏高，负值意味着低估用电需求。采用MAE、RMSE、平均偏差和绝对误差95%分位数共同描述典型偏差与尾部偏差。')
eq(r'e_i=\widehat{N}_i^{P}-N_i^{P},\quad \mathrm{MAE}=\frac{1}{n}\sum_i|e_i|,\quad \mathrm{RMSE}=\sqrt{\frac{1}{n}\sum_i e_i^2}')
er=checks['errors']
tab('净负荷功率预测的外样本误差',['指标','MAE','RMSE','平均偏差','绝对误差95%分位'],[['数值 / kW',f(er['MAE']),f(er['RMSE']),f(er['bias']),f(er['p95_abs'])]],[3.2]*5)
fig(HERE/'图/12_误差诊断.png','净负荷预测与实际的分布及预测误差',15)
p('平均偏差为−13.66 kW，存在轻微低估；RMSE高于MAE，表明少量大误差会放大二次损失。绝对误差95%分位为832.61 kW，对应单时段138.77 kWh，仅用于解释量级，不能作为保证覆盖95%未来需求的储能容量。净负荷可能接近零，故不采用其MAPE作为主指标。该误差针对日前岭回归，不等同于更新后的光伏预报误差。')
h('5.7.4 对比验证',3)
p(r'首先进行数值与物理对比。问题1由独立原始与对偶模型、双单纯形和内点法验证，目标差约$7.28\times10^{-12}$元。12组全年策略共132项物理与费用检查的最大误差为$5.82\times10^{-11}$；五份工作簿的288720个购电时段值独立回读，最大差异约$1.2\times10^{-10}$。另有61项未来信息污染测试支持已检查路径的信息边界。')
p('其次比较相同信息条件下的问题3策略A与D。逐日费用先按相同价格系数校正日初日末库存，再计算配对节省；以7日连续区块作2000次移动区块重采样，固定随机种子20260912。这样保留部分周内相关性，避免把48096个时段当作相互独立样本。')
eq(r'\Delta J_d=J_{A,d}^{\mathrm{adj}}-J_{D,d}^{\mathrm{adj}}')
co=checks['comparison']
p(f'策略D在334天中的{co["positive_days"]}天实现正节省，日均库存校正节省为{f(co["mean_gain"])}元；重采样均值的2.5%和97.5%分位为{f(co["ci_low"])}元和{f(co["ci_high"])}元。该区间是固定年度样本与7日区块设定下的经验不确定性范围；季节非平稳性、区块长度和仅一年数据限制其外推，不作跨年份收益保证。')
fig(HERE/'图/14_配对比较.png','策略D相对A的配对节省及区块重采样分布',15)
h('5.8 模型深化与扩展验证',2)
p('为抑制代表情景中的大额紧急购电，在原期望费用模型中引入最坏情景损失上界。设各情景紧急费用为损失，以非负权重控制其附加惩罚：')
eq(r'\min J_{\lambda}=J_{\mathrm{base}}+\lambda Z,\qquad Z\geq\sum_t5p_tR_t^{(s)},\quad s=1,\ldots,K')
p('新增变量和约束均为线性，因此仍可采用原稀疏线性规划求解器。权重候选为0、0.1、0.3和1，仅在1月17—31日选择，再在四季24日验证；这是一项针对尾部成本的模型扩展，不改变已有结果表的信息条件。')
p('实测四种权重在1月的库存校正费用均为936469.26元，四季24日均为1022316.93元，未取得可辨别的费用改善，因此按较简原则保留权重0。仅提高现有三个情景的风险惩罚不足以修复未被情景覆盖的持续系统偏差；后续应优先扩充极端残差情景、校准情景权重，并引入带条件预测的实时储能优化。未验证改善不写入主方案收益。')
'''
s=s[:a]+more+s[a:]
s=s.replace("p('可将电池执行规则改进", "p('在已完成的风险惩罚扩展基础上，可将电池执行规则改进")
# 添加实测汇总输入。
s=s.replace("doc=setup();notes=[]", "checks=json.loads((HERE/'检验结果/新增检验汇总.json').read_text(encoding='utf-8'))\ndoc=setup();notes=[]")
# 截断原参考文献和原代码附录，后续按新模块生成。
s=s[:s.index("h('参考文献')")]
exec(compile(s,str(BASE/'build_body_generated.py'),'exec'),globals())

h('参考文献')
refs=[
'SCIPY DEVELOPERS. scipy.optimize.linprog[EB/OL]. [2026-09-12]. https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linprog.html.',
'BOYD S, VANDENBERGHE L. Convex optimization[M]. Cambridge: Cambridge University Press, 2004.',
'HYNDMAN R J, ATHANASOPOULOS G. Forecasting: principles and practice[M/OL]. 3rd ed. Melbourne: OTexts, 2021[2026-09-12]. https://otexts.com/fpp3/.',
'RAWLINGS J B, MAYNE D Q, DIEHL M M. Model predictive control: theory, computation, and design[M/OL]. 2nd ed. Nob Hill Publishing, 2026[2026-09-12]. https://sites.engineering.ucsb.edu/~jbraw/mpc/.'
]
for i,text in enumerate(refs,1):
    pp=p('',False);pp.paragraph_format.left_indent=Pt(20);pp.paragraph_format.first_line_indent=Pt(-20);pp.paragraph_format.line_spacing=Pt(16)
    pp.add_run('[');bookmark(pp,'bib'+str(i),lambda i=i:field(pp,'SEQ Bibliography \\* ARABIC',i));pp.add_run('] '+text)
    pp.alignment=WD_ALIGN_PARAGRAPH.LEFT
    for rr in pp.runs:rr.font.size=Pt(10.5)

# 将图引用并入相邻分析段，避免题注下面再重复一遍题注文字。
paras=list(doc.paragraphs)
fig_paragraphs={
1:'本文沿用问题2和问题3的物理约束',2:'附件1提供日内电价',3:'能量流图将母线',
4:'从计算结果可以看出',5:'典型日曲线显示',6:'月度统计将全年',7:'附件3每次发布24个',
8:'热力图中的红色',9:'由A到B',10:'图示对应当天价格曲线',11:'当日曲线已知时，滚动调整方案',
12:'检验分为灵敏度',13:'以零变化线为参照',14:'四种情形的储电量',
15:'平均偏差为',16:'策略D在334天中的'}
for i,pp in enumerate(paras):
    match=re.match(r'图(\d+)给出',''.join(pp._p.xpath('.//w:t/text()')))
    if not match:continue
    num=match.group(1)
    target=next((x for x in paras if x.text.startswith(fig_paragraphs[int(num)])),None)
    assert target is not None,('missing figure analysis',num)
    if target is not None:
        target.add_run(' 参见图');ref(target,'fig'+num,num);target.add_run('。')
        pp._p.getparent().remove(pp._p)
# 将正文已有文献标注替换为真实REF域，保持正文其余数学节点不变。
for pp in list(doc.paragraphs):
    for rr in list(pp.runs):
        if not re.search(r'\[([1-4](?:,[1-4])*)\]',rr.text):continue
        text=rr.text;parent=rr._r.getparent();pos=parent.index(rr._r);parent.remove(rr._r)
        temp=doc.add_paragraph()
        for part in re.split(r'(\[[1-4](?:,[1-4])*\])',text):
            if re.fullmatch(r'\[[1-4](?:,[1-4])*\]',part):
                temp.add_run('[')
                for j,v in enumerate(part[1:-1].split(',')):
                    if j:temp.add_run(',')
                    ref(temp,'bib'+v,v)
                temp.add_run(']')
            else:temp.add_run(part)
        for node in list(temp._p):
            if node.tag!=qn('w:pPr'):parent.insert(pos,node);pos+=1
        temp._p.getparent().remove(temp._p)

# 给正文关键方程加入交叉引用，不将数学公式变成图片。
targets=[('后续各问均在上述约束下求解。',[2,3,4]),('决策变量由144个购电量',[6]),('日前购电量在三个情景间共享',[11,12])]
for needle,nums in targets:
    pp=next((x for x in doc.paragraphs if needle in x.text),None)
    if pp is not None:
        pp.add_run(' 相关关系见式')
        for j,n in enumerate(nums):
            if j:pp.add_run('、')
            pp.add_run('(');ref(pp,'eq'+str(n),n);pp.add_run(')')
        pp.add_run('。')

br();h('附录A　支撑材料与模块运行说明')
manifest=json.loads((HERE/'TXT程序包/文件清单.json').read_text(encoding='utf-8'))
p('程序按输入、预测、优化、执行、验证和绘图分层封装。TXT文件保存完整UTF-8 Python源码，恢复脚本核对SHA256后生成同名PY模块；无需从Word复制长代码。原始附件放入input，所有结果写入程序包内部目录。正文中的指定日期结果仍使用前版已经独立核验的完整轨迹。')
tab('程序包功能索引',['TXT文件','功能'],[[r['file'],r['purpose']] for r in manifest],[6,10])
for text in (HERE/'TXT程序包/运行说明.txt').read_text(encoding='utf-8').splitlines():p(text,False)
p('输入：题设附件1至4和附件5模板。中间结果：results中的逐时段轨迹、逐日费用、预测缓存及灵敏度表。检验输出：audit和检验结果。依赖：NumPy、SciPy、pandas、openpyxl、matplotlib。运行顺序为附件解析、预测选型、全年回放、灵敏度、独立校验和图形生成。基础计算与新增检验均保留独立入口。')
br();h('附录B　人工智能工具使用声明')
p('本研究在资料核对、程序审查、计算复核、模型扩展试验、图形绘制、论文文字修订及Word公式排版中使用OpenAI Codex辅助。建模所用数值输入为题设附件；正文中的新增数值来自所附程序的实际执行结果，未以生成式文本代替数值计算。')
p('AI参与范围包括提出检验方案、编写和调整Python程序、整理参考文献信息、转换LaTeX公式为Word数学对象、建立自动编号及交叉引用。AI提出的风险惩罚扩展已作验证，未观察到收益，因此没有宣称主模型性能提高。工具输出与程序运行记录保存在本次工作目录及交互记录中。')
p('参赛提交者应对题意解释、模型假设、计算结果、引用与最终内容负责。正式提交前须依据实际使用情况补齐其他AI工具、具体版本、调用日期及完整交互记录；本声明只记录本次可确认的Codex参与情况，不代替尚未提供的完整使用日志，也不作“全部由人工独立完成”的不实声明。所提供的2026年论文格式规范没有具体AI日志模板，相关专项要求应以赛事实际发布文件为准。')

def code_block(source,line_height=10.5):
    for line in source.splitlines():
        pp=doc.add_paragraph();pf=pp.paragraph_format;pf.first_line_indent=Pt(0);pf.space_before=pf.space_after=Pt(0);pf.line_spacing=Pt(line_height);pf.alignment=WD_ALIGN_PARAGRAPH.LEFT;pf.widow_control=False
        rr=pp.add_run(line or ' ');rr.font.name='Consolas';rr.font.size=Pt(8);rr._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'宋体')
br();h('附录C　恢复入口与依赖清单')
p('先放入原始附件，再执行恢复脚本。smoke用于附件解析及问题1双求解器验证；all执行完整管线。脚本仅向本包内写入，不删除工程原文件。')
code_block((HERE/'TXT程序包/restore_and_run.txt').read_text(encoding='utf-8'))
for i,item in enumerate(manifest,1):
    br();h(f'附录D.{i}　{item["purpose"]}')
    p('源文件：'+item['file']+'；恢复文件：src/'+item['module']+'。')
    source=(HERE/'TXT程序包'/item['file']).read_text(encoding='utf-8')
    if item['module']=='run.py':p('本模块负责阶段调度；all从输入重建计算管线，annual优先读取已有轨迹，annual_force强制重算。为复核结果，应保留运行时依赖版本和输入校验值。')
    elif item['module']=='extended_checks.py':p('本模块将压力试验、误差统计、配对区块重采样和风险权重实验分为独立函数。权重选择使用1月，四季24日用于后续验证，固定随机种子保证重采样复现。')
    code_block(source,10 if item['module']=='forecasting.py' else 10.5)

# 表格题注SEQ与书签；保留章节前缀，正文引用可以自动更新。
table_index=0
for pp in doc.paragraphs:
    match=re.match(r'表5-(\d+) (.*)',pp.text)
    if not match:continue
    table_index+=1;title=match.group(2);pp.clear();pp.add_run('表')
    bookmark(pp,'tbl'+str(table_index),lambda:field(pp,'SEQ Table \\* ARABIC',table_index));pp.add_run(' '+title)
for i in [1,4]:
    pp=next((x for x in doc.paragraphs if ('问题1的优化结果' if i==1 else '不同预测方法的外样本误差') in x.text),None)
    # 题注已具备域书签；具体表的引用在段落内增加。
for pp in doc.paragraphs:
    if '从费用构成可以看出' in pp.text:
        pp.add_run(' 费用项与表');ref(pp,'tbl'+str(5),5);pp.add_run('对应。');break
for el in list(doc.element.iter(qn('w:pBdr'))):el.getparent().remove(el)
# 章节使用段前分页，避免代码刚好满页时单独的分页符产生空白页。
paras=list(doc.paragraphs)
for i,pp in enumerate(paras):
    if pp.text.strip() or not pp._p.xpath('.//w:br[@w:type="page"]'):continue
    if i+1<len(paras):paras[i+1].paragraph_format.page_break_before=True
    for prior in reversed(paras[:i]):
        if prior.text.strip() or prior._p.xpath('.//w:drawing'):break
        if prior._p.getparent() is not None:prior._p.getparent().remove(prior._p)
    if pp._p.getparent() is not None:pp._p.getparent().remove(pp._p)

for run in doc.element.iter(qn('m:r')):
    tnode=run.find(qn('m:t'))
    if tnode is not None and tnode.text in ['min','max','exp']:
        pr=run.find(qn('m:rPr'))
        if pr is None:pr=OxmlElement('m:rPr');run.insert(0,pr)
        sty=OxmlElement('m:sty');sty.set(qn('m:val'),'p');pr.append(sty)

doc.core_properties.title='基于滚动预测与储能协同调度的微网购电策略优化研究'
doc.save(HERE/'微网购电策略论文_深化检验版.docx')
(HERE/'论文正文与公式源.md').write_text('\n\n'.join(notes),encoding='utf-8')
(HERE/'公式LaTeX源.tex').write_text('\n\n'.join('\\[\n'+x+'\n\\]' for x in FORMULAS),encoding='utf-8')
print(json.dumps({'formulas':n_eq,'figures':n_fig,'tables':table_index},ensure_ascii=False))
