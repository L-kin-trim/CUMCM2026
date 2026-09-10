from pathlib import Path
import hashlib,json,zipfile
root=Path(__file__).resolve().parents[1]
main=[
 'result1_final.xlsx','result2_final.xlsx','result3_final.xlsx','result4-2_final.xlsx','result4-3_final.xlsx',
 'paper/微网与外部电网电力调控策略论文.docx','paper/微网与外部电网电力调控策略论文.pdf','paper/论文正文.md',
 'audit/数据审计报告.md','audit/结果校验报告.md','README.md','requirements-lock.txt','references.bib','run_all.ps1'
]
manifest=[]
for rel in main:
    p=root/rel;assert p.exists() and p.stat().st_size>0,rel
    manifest.append({'文件':rel,'字节':p.stat().st_size,'SHA256':hashlib.sha256(p.read_bytes()).hexdigest()})
(root/'交付清单.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
archive=root/'C题微网建模完整交付包.zip'
include_roots=['input','src','results','figures','audit','templates']
files=[root/x for x in main]+[root/'交付清单.json']
for d in include_roots:
    files.extend(p for p in (root/d).rglob('*') if p.is_file())
files.extend((root/'paper'/'equations').glob('*.png'))
files=sorted(set(files))
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in files:
        if '__pycache__' in p.parts or p.name.startswith('图表总览'):continue
        z.write(p,Path('C题微网建模')/p.relative_to(root))
print(archive,archive.stat().st_size,len(files))
