import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const src=path.dirname(fileURLToPath(import.meta.url)), root=path.dirname(src), review=path.dirname(root), project=path.dirname(review);
const data=JSON.parse(await fs.readFile(path.join(root,'results/工作簿修订数据.json'),'utf8'));
const specs=[['result1_final.xlsx','q1','问题1'],['result2_final.xlsx','q2','问题2'],['result3_final.xlsx','q3_D','问题3'],['result4-2_final.xlsx','q42','问题4'],['result4-3_final.xlsx','q43_D','问题4']];
const preview=process.argv.includes('--preview');
const qa=path.join(review,'08_验证记录/表格');await fs.mkdir(qa,{recursive:true});
for(const [file,tag,group] of specs){
 const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(path.join(project,file)));
 if(preview){
  for(const sn of (tag==='q1'?['计划购电量','充放电量']:['计划购电量','充放电量','紧急购电量',...(tag.includes('D')?['调整购电量']:[])])){
   const b=await wb.render({sheetName:sn,range:sn.includes('充放')?'A1:F8':sn.includes('紧急')?'A1:C8':tag==='q1'?'A138:B145':'EM1:EQ4',scale:1.4});
   await fs.writeFile(path.join(qa,`原始_${tag}_${sn}.png`),new Uint8Array(await b.arrayBuffer()));
  }
  continue;
 }
 const names=['计划购电量',...(tag.includes('D')?['调整购电量']:[])];
 for(const sn of names){wb.worksheets.getItem(sn).getRange(tag==='q1'?'A145':'EO1').values=[['00:00-00:10']];}
 const s=wb.worksheets.add('费用核算');
 if(tag==='q1'){
  const q=JSON.parse(await fs.readFile(path.join(root,'results/q1_summary.json'),'utf8'));
  s.getRange('A1:B1').values=[['项目','数值或说明']];
  s.getRange('A2:B7').values=[['全天购电量（kWh）',q.total_energy],['全天购电费（元）',q.cost],['日初储电量（kWh）',q.initial],['日末储电量（kWh）',q.final],['时间说明','原末行按本日00:00-00:10解释，购电数据未更改'],['数据依据','附件1、附录1；充放电效率各0.9；功率按区间右端对齐']];
  s.getRange('A1:A7').format.columnWidth=28;s.getRange('B1:B7').format.columnWidth=78;s.getRange('B2:B5').setNumberFormat('0.0000');
 }else{
  s.getRange('A1:N1').values=[['日期','计划量kWh','最终常规量kWh','紧急量kWh','计划费元','增购费元','违约费元','退款元','净调整费元','紧急费元','总费元','日初储电kWh','日末储电kWh','调整附加费元']];
  const rows=data[tag].daily;
  s.getRange('A2:N335').values=rows.map(r=>[r.date,r.G0,r.G,r.R,r.base,r.increase,r.cancel,r.refund,null,r.emergency,null,r.S0,r.Send,r.surcharge]);
  s.getRange('I2:I335').formulas=rows.map((_,i)=>[`=F${i+2}+G${i+2}-H${i+2}`]);
  s.getRange('K2:K335').formulas=rows.map((_,i)=>[`=E${i+2}+I${i+2}+J${i+2}`]);
  s.getRange('A336').values=[['合计']];
  for(const col of ['B','C','D','E','F','G','H','I','J','K','N'])s.getRange(`${col}336`).formulas=[[`=SUM(${col}2:${col}335)`]];
  s.getRange('A338:B341').values=[['时间说明','原EO列按本日00:00-00:10解释，原购电数据未更改'],['费用说明','计划/调整工作表的全天购电费不含紧急购电；完整费用见K列'],['调整约定','按上一有效计划结算；退还取消部分原款并收50%违约费'],['电价信息',tag.startsWith('q4')?'本表为当日电价已知的条件基准；历史价格预测扩展另见论文':'固定日内电价来自附件1']];
  s.getRange('A1:N336').format.columnWidth=17;s.getRange('A1:N1').format.rowHeight=34;s.getRange('A1:N1').format.wrapText=true;
  s.getRange('B2:N336').setNumberFormat('#,##0.0000');s.freezePanes.freezeRows(1);
 }
 s.getUsedRange().format.font.name='Microsoft YaHei';s.getRange(tag==='q1'?'A1:B1':'A1:N1').format.fill='#EAEAEA';
 s.getRange(tag==='q1'?'A1:B1':'A1:N1').format.font.bold=true;
 console.log(file,(await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:5},maxChars:500})).ndjson);
 const dest=path.join(review,'06_错误说明与纠正',group);await fs.mkdir(dest,{recursive:true});
 const output=await SpreadsheetFile.exportXlsx(wb);await output.save(path.join(dest,file.replace('_final','_修订')));
 for(const [sn,rng] of [['计划购电量',tag==='q1'?'A138:B145':'EM1:EQ4'],['费用核算',tag==='q1'?'A1:B7':'A1:K5']]){
  const b=await wb.render({sheetName:sn,range:rng,scale:1.4});await fs.writeFile(path.join(qa,`修订_${tag}_${sn}.png`),new Uint8Array(await b.arrayBuffer()));
 }
 console.log('SAVED',file);
}

