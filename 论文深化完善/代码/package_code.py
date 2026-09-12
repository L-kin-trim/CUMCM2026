"""将计算程序按职责拆为UTF-8 TXT；恢复为PY后做独立运行验证。"""
from pathlib import Path
import ast,json,hashlib,shutil
HERE=Path(__file__).resolve().parent.parent
WORK=HERE.parent;SRC=WORK/'审查与完善/07_复现代码与数据/src'
OUT=HERE/'TXT程序包';OUT.mkdir(exist_ok=True)
text=(SRC/'model.py').read_text(encoding='utf-8');tree=ast.parse(text)
functions={n.name:ast.get_source_segment(text,n) for n in tree.body if isinstance(n,ast.FunctionDef)}
comments={
'dump':'将NumPy标量转为JSON可序列化数值；UTF-8保存中文检查结果。',
'time_label':'输入10分钟时段索引，输出24小时制时间标签。',
'interval':'把左端及可选右端索引转换为区间标签。',
'align_time':'模板按区间左端匹配，末列解释为本日首时段；这是论文约定。',
'_minute':'把Excel时间或次日标记转换为分钟索引。',
'load_data':'读取附件1至4及模板，验证形状、非负、有限值和日期顺序；生成数据审计和NPZ缓存。',
'forecast':'仅以目标日前的样本预测；参数method选择六种方法，fallback处理无历史情形。返回144个功率值。',
'build_forecasts':'对365日逐一调用因果预测器；生成所有候选，不用外样本选择模型。',
'metrics':'返回MAE、RMSE、归一化MAE和避开近零实际值的MAPE；功率误差单位kW。',
'lp_structure':'按G、各情景C/D/R/W/S、终端绝对偏差、增减购电量布局建立稀疏矩阵；按规模和效率缓存。',
'optimize_day':'共同计划连接各情景；old为空表示日前，否则对上一有效计划增减。返回计划与首情景状态；该状态不是实际回放。',
'recourse':'只使用当前净负荷及库存。先充/放电再补购；输出C,D,R,W和下一库存，均以kWh计。',
'interpolate_hourly_forecast':'用发布时间已知的左端锚点插值整点预报；返回10分钟分辨率未来24小时功率。',
'scenarios':'从最近30个完整日残差按日总量排序选代表曲线；margin乘标准差，保持日内相关结构。',
'merge_emergency_intervals':'合并相邻紧急购电时段，核验合并前后电量守恒。',
'run_policy':'逐日制定计划并在指定发布时间更新未执行部分；每个10分钟时段实测执行，跨日不重置SOC。save=False禁止导出。',
'validate_solution':'从轨迹和实际输入独立重算11类等式及边界；超过1e-6立即失败，不只依赖优化器成功标志。'}
groups=[('common','公共参数和文件接口',['dump','time_label','interval','align_time','_minute']),('data_io','附件解析与审计',['load_data']),('forecasting','因果预测与误差',['forecast','build_forecasts','metrics','interpolate_hourly_forecast','scenarios']),('optimization','线性规划求解',['lp_structure','optimize_day']),('dispatch','运行与交易结算',['recourse','merge_emergency_intervals','run_policy']),('validation','物理与费用验证',['validate_solution'])]
header='''from pathlib import Path
import json,hashlib,datetime as dt
from functools import lru_cache
import numpy as np
import pandas as pd
from openpyxl import load_workbook
from scipy.optimize import linprog
from scipy.sparse import lil_matrix
from scipy.interpolate import PchipInterpolator
ROOT=Path(__file__).resolve().parents[1]
DT=1/6;T=144;SEED=20260910
DATES=pd.date_range('2025-01-01',periods=365)
METHODS=['mean','ma7','ma14','ma30','ewma','ridge']
'''
manifest=[]
def put(name,code,purpose):
    ast.parse(code);dest=OUT/(name+'.txt');dest.write_text(code,encoding='utf-8')
    manifest.append(dict(file=dest.name,module=name+'.py',purpose=purpose,sha256=hashlib.sha256(dest.read_bytes()).hexdigest()))
for i,(name,purpose,names) in enumerate(groups):
    code='"""'+purpose+'。输入输出单位沿用论文；发生约束错误时直接报错。"""\n'
    code+=header if i==0 else ''.join('from '+g[0]+' import *\n' for g in groups[:i])+'from common import _minute\n'
    for fn in names:
        s=functions[fn];lines=s.splitlines();ix=next(j for j,l in enumerate(lines) if l.startswith('def '))
        lines.insert(ix+1,'    # '+comments[fn])
        if fn=='lp_structure':lines.insert(0,'@lru_cache(maxsize=128)')
        code+='\n\n'+'\n'.join(lines)+'\n'
    code=code.replace('统一勘误','统一解释').replace('原末列勘误','原末列解释')
    put(name,code,purpose)
put('model','"""兼容入口：向原主程序导出分功能模块。"""\n'+''.join('from '+g[0]+' import *\n' for g in groups),'模块统一接口')
put('run',(SRC/'run.py').read_text(encoding='utf-8'),'四问计算 参数选型 灵敏度实验')
cert=(SRC/'q1_certificate.py').read_text(encoding='utf-8').replace("ROOT = HERE.parents[2]","ROOT = HERE.parent").replace("'附件'","'input'")
put('q1_certificate',cert,'独立求解与原始对偶检验')
extended=(HERE/'代码/extended_checks.py').read_text(encoding='utf-8')
start=extended.index('WORK=HERE.parents[1]');end=extended.index('\nORIGINAL_OPTIMIZER')
extended=extended[:start]+"import dispatch as m\nfrom validation import validate_solution\nm.validate_solution=validate_solution\nSRC=HERE\nR=HERE.parent/'results'\nOUT=HERE.parent/'检验结果';OUT.mkdir(exist_ok=True)\n"+extended[end:]
put('extended_checks',extended,'压力 误差 重采样及风险模型扩展')
# 仅提取因果测试，不携带历史有问题的表格导出入口。
delivery=(SRC/'deliver.py').read_text(encoding='utf-8');dtree=ast.parse(delivery)
causal=next(ast.get_source_segment(delivery,n) for n in dtree.body if isinstance(n,ast.FunctionDef) and n.name=='causality')
put('causality','from model import *\n'+causal+"\nif __name__=='__main__':causality()\n",'未来信息污染检验')
figcode=(HERE/'代码/make_figures.py').read_text(encoding='utf-8').replace("R=HERE.parent/'审查与完善/07_复现代码与数据/results'","R=HERE/'results'")
put('make_figures',figcode,'新增八图复现')
legacy=(SRC/'figures.py').read_text(encoding='utf-8')
put('figures_legacy',legacy,'基础结果图形复现')
added=(WORK/'论文范例对齐修订/图文增强版/make_added_figures.py').read_text(encoding='utf-8')
added=added.replace("HERE.parents[1]/'审查与完善/07_复现代码与数据/results'","HERE.parent/'results'")
put('figures_added',added,'前版六幅分析图复现')
restore='''"""直接运行 python restore_and_run.txt --smoke；只向本包的src和结果目录写入。"""
from pathlib import Path
import argparse,subprocess,sys,hashlib,json
root=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--smoke',action='store_true');parser.add_argument('--all',action='store_true');args=parser.parse_args()
for folder in ['src','input','audit','results','计算结果','检验结果','图','figures']: (root/folder).mkdir(exist_ok=True)
manifest=json.loads((root/'文件清单.json').read_text(encoding='utf-8'))
for entry in manifest:
    raw=(root/entry['file']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==entry['sha256'],entry['file']
    (root/'src'/entry['module']).write_bytes(raw)
def run(name,*argv):subprocess.run([sys.executable,str(root/'src'/name),*argv],check=True)
if args.smoke:run('run.py','--stage','q1');run('q1_certificate.py')
if args.all:
    run('run.py','--stage','all');run('q1_certificate.py');run('causality.py');run('extended_checks.py');run('make_figures.py');run('figures_legacy.py');run('figures_added.py')
print('模块恢复及请求的运行阶段已完成。')
'''
(OUT/'restore_and_run.txt').write_text(restore,encoding='utf-8')
(OUT/'文件清单.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'requirements.txt').write_text('numpy\nscipy\npandas\nopenpyxl\nmatplotlib\npillow\n',encoding='utf-8')
(OUT/'运行说明.txt').write_text('''功能模块均为UTF-8 TXT，内容是完整Python源代码。恢复脚本可直接由Python运行，无须手工改扩展名。
1. 安装Python 3.12及依赖：python -m pip install -r requirements.txt
2. 将附件1.xlsx至附件4.xlsx和附件5中的五份原始模板放在本目录input文件夹（不要使用final结果代替模板）。
3. 运行 python restore_and_run.txt --smoke，核验附件解析和问题1两个独立求解器。
4. 运行 python restore_and_run.txt --all，执行全量预测选型、12组全年回放、24日敏感性、因果测试及新增检验。全量计算耗时明显长于smoke。
5. 可单独运行 src/run.py --stage forecast、annual、sensitivity。强制重算全年用annual_force。单独阶段须有前序结果。
6. results保存全精度NPZ及CSV；audit保存11类约束和因果检查；计算结果保存问题1证书；检验结果保存新增检验。当前包不执行历史Excel导出实现，避免覆写原表。
7. 各模块功能、SHA256与恢复后的文件名见文件清单.json。不得更改单个TXT后继续使用旧校验清单。
8. figures_legacy和figures_added重现基础结果图及前版六图，make_figures重现本次新增八图；问题1独立轨迹图由q1_certificate生成。
''',encoding='utf-8')
print(len(manifest),'TXT模块')
if __name__=='__main__':pass
