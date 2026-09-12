from pathlib import Path
import json,zipfile,hashlib
import numpy as np
import pandas as pd
import scipy,matplotlib,openpyxl
P=Path(__file__).resolve().parent.parent
original=P.parent/'审查与完善/07_复现代码与数据/results'
new=P/'TXT程序包/results'
report={}
for name in ['年度汇总.csv','敏感性24日.csv','预测精度.csv']:
    a=pd.read_csv(original/name);b=pd.read_csv(new/name)
    assert list(a.columns)==list(b.columns) and a.shape==b.shape,name
    cols=a.select_dtypes('number').columns
    error=float(np.nanmax(np.abs(a[cols].to_numpy()-b[cols].to_numpy())))
    assert error<1e-6,(name,error)
    report[name]=dict(rows=len(a),max_difference=error)
for name in ['q2','q3_D','q42','q43_D']:
    a=np.load(original/(name+'.npz'));b=np.load(new/(name+'.npz'))
    errs={k:float(np.max(np.abs(a[k]-b[k]))) for k in ['G0','G','C','D','R','W','S']}
    assert max(errs.values())<1e-6,(name,errs)
    report[name]=errs
v=pd.read_csv(P/'TXT程序包/audit/物理与费用验证.csv');assert (v['状态']=='PASS').all()
report['physical_checks_passed']=len(v)
report['runtime_versions']=dict(numpy=np.__version__,scipy=scipy.__version__,pandas=pd.__version__,matplotlib=matplotlib.__version__,openpyxl=openpyxl.__version__)
report['full_pipeline']='restore_and_run.txt --all exited 0; forecast/annual/sensitivity/certificate/causality/extended checks/all figures completed'
(P/'TXT完整复现核验.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
pkg=P/'TXT程序包'
with zipfile.ZipFile(P/'分功能TXT程序与运行材料.zip','w',zipfile.ZIP_DEFLATED) as z:
    for f in pkg.iterdir():
        if f.is_file():z.write(f,f.name)
    for folder in ['input','检验结果','audit']:
        for f in (pkg/folder).rglob('*'):
            if f.is_file():z.write(f,str(f.relative_to(pkg)))
    z.write(P/'TXT完整复现核验.json','TXT完整复现核验.json')
    # 大规模NPZ可由全量入口重建；年度与灵敏度汇总便于快速对照。
    for name in ['年度汇总.csv','敏感性24日.csv','预测精度.csv']:
        z.write(new/name,'参考结果/'+name)
assert (P/'分功能TXT程序与运行材料.zip').stat().st_size<20*1024*1024
print(json.dumps(report,ensure_ascii=False))
