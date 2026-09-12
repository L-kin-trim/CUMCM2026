from pathlib import Path
import re
p=Path(__file__).with_name('build_paper.py')
s=p.read_text(encoding='utf-8')
fixes={
"eq(r'e_i=":r"eq(r'e_i=\widehat{N}_i^{P}-N_i^{P},\quad \mathrm{MAE}=\frac{1}{n}\sum_i|e_i|,\quad \mathrm{RMSE}=\sqrt{\frac{1}{n}\sum_i e_i^2}')",
"eq(r'Delta":r"eq(r'\Delta J_d=J_{A,d}^{\mathrm{adj}}-J_{D,d}^{\mathrm{adj}}')",
"eq(r'min J_":r"eq(r'\min J_{\lambda}=J_{\mathrm{base}}+\lambda Z,\qquad Z\geq\sum_t5p_tR_t^{(s)},\quad s=1,\ldots,K')",
"p(r'首先进行数值":r"p(r'首先进行数值与物理对比。问题1由独立原始与对偶模型、双单纯形和内点法验证，目标差约$7.28\times10^{-12}$元。12组全年策略共132项物理与费用检查的最大误差为$5.82\times10^{-11}$；五份工作簿的288720个购电时段值独立回读，最大差异约$1.2\times10^{-10}$。另有61项未来信息污染测试支持已检查路径的信息边界。')"
}
for prefix,value in fixes.items():
    a=s.index(prefix);b=s.index('\n',a);s=s[:a]+value+s[b:]
fix="""
for run in doc.element.iter(qn('m:r')):
    tnode=run.find(qn('m:t'))
    if tnode is not None and tnode.text in ['min','max','exp']:
        pr=run.find(qn('m:rPr'))
        if pr is None:pr=OxmlElement('m:rPr');run.insert(0,pr)
        sty=OxmlElement('m:sty');sty.set(qn('m:val'),'p');pr.append(sty)
"""
s=s.replace("doc.core_properties.title=",fix+"\ndoc.core_properties.title=")
p.write_text(s,encoding='utf-8')
