from pathlib import Path
import json,re,zipfile,hashlib
import pymupdf as fitz
from lxml import etree
P=Path(__file__).resolve().parent
d=fitz.open(P/'排版检查.pdf');out=P/'最终逐页检查';out.mkdir(exist_ok=True)
pages=[];changed=[]
for i,pg in enumerate(d):
    text=pg.get_text();dest=out/f'page-{i+1}.png';previous=hashlib.sha256(dest.read_bytes()).hexdigest() if dest.exists() else None
    pg.get_pixmap(matrix=fitz.Matrix(1.4,1.4)).save(dest)
    if previous!=hashlib.sha256(dest.read_bytes()).hexdigest():changed.append(i+1)
    pages.append({'page':i+1,'start':text[:100],'end':text[-120:],'characters':len(text)})
appendix=next(i+1 for i,pg in enumerate(d) if '附录A' in pg.get_text())
z=zipfile.ZipFile(P/'微网购电策略论文_图文增强版.docx')
x=etree.fromstring(z.read('word/document.xml'))
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
plain='\n'.join(x.xpath('//w:t/text()',namespaces=ns))
raw=re.findall(r'\\(?:frac|sum|eta|widehat|begin|end|leq|geq|Delta|mathrm|mathsf|boldsymbol)\b|\$\$',plain)
report={'pages':len(d),'abstract_pages':1,'body_including_references_pages':appendix-2,'appendix_start_page':appendix,'native_math_objects':len(x.xpath('//m:oMath',namespaces=ns)),'display_math_objects':len(x.xpath('//m:oMathPara',namespaces=ns)),'raw_latex_commands_in_word':raw,'nested_math_paragraphs':len(x.xpath('//m:oMathPara//m:oMathPara',namespaces=ns)),'tables':len(x.xpath('//w:tbl',namespaces=ns)),'docx_bytes':(P/'微网购电策略论文_图文增强版.docx').stat().st_size,'margins':[dict(a.attrib) for a in x.xpath('//w:pgMar',namespaces=ns)]}
assert report['body_including_references_pages']<=30
assert not raw and not report['nested_math_paragraphs']
assert report['docx_bytes']<20*1024*1024
(P/'最终结构检查.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
(out/'页内容索引.json').write_text(json.dumps(pages,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
print('CHANGED_PAGES',changed)
for r in pages:print(r['page'],r['start'].replace('\n',' ')[:65])
