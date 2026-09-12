from pathlib import Path
import json,re,zipfile
import pymupdf as fitz
from lxml import etree
P=Path(__file__).resolve().parent.parent
docx=P/'微网购电策略论文_深化检验版.docx'
# 删除Word保存时写入的个人元数据，不改变版面。
with zipfile.ZipFile(docx) as z:parts={n:z.read(n) for n in z.namelist()}
x=etree.fromstring(parts['docProps/core.xml'])
for e in x:
    if etree.QName(e).localname in ['creator','lastModifiedBy']:e.text=''
parts['docProps/core.xml']=etree.tostring(x,xml_declaration=True,encoding='UTF-8',standalone=True)
with zipfile.ZipFile(docx,'w',zipfile.ZIP_DEFLATED) as z:
    for n,data in parts.items():z.writestr(n,data)
x=etree.fromstring(parts['word/document.xml'])
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
simple=x.xpath('//w:fldSimple/@w:instr',namespaces=ns);complex_=x.xpath('//w:instrText/text()',namespaces=ns);fields=simple+complex_
names=x.xpath('//w:bookmarkStart/@w:name',namespaces=ns)
refs=[s.split()[1] for s in fields if s.strip().startswith('REF ')]
assert all(r in names for r in refs),refs
d=fitz.open(P/'排版检查.pdf');texts=[p.get_text() for p in d]
app=next(i+1 for i,t in enumerate(texts) if '附录A' in t)
body='\n'.join(texts[:app-1])
assert not any(v in body for v in ['widehat','mathrm','frac','lambda','rac1','错误!','Error!'])
assert app-2<=30,(app,len(d))
assert sum('SEQ Equation' in s for s in fields)==28
assert sum('SEQ Figure' in s for s in fields)==16
out=P/'逐页检查';out.mkdir(exist_ok=True)
for i,p in enumerate(d):p.get_pixmap(matrix=fitz.Matrix(1.25,1.25)).save(out/f'page-{i+1}.png')
report=dict(total_pages=len(d),abstract_pages=1,body_with_references_pages=app-2,appendix_start=app,figures=16,equation_seq=28,crossrefs=len(refs),all_targets_resolve=True,docx_bytes=docx.stat().st_size)
(P/'最终结构检查.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
(out/'页索引.json').write_text(json.dumps([dict(page=i+1,start=t[:110],end=t[-110:]) for i,t in enumerate(texts)],ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
