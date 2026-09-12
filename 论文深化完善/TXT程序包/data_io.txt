"""附件解析与审计。输入输出单位沿用论文；发生约束错误时直接报错。"""
from common import *
from common import _minute


def load_data():
    # 读取附件1至4及模板，验证形状、非负、有限值和日期顺序；生成数据审计和NPZ缓存。
    if not (ROOT/'input'/'附件1.xlsx').exists():
        raise FileNotFoundError('请将附件1至4及附件5模板放入本复现目录的input文件夹')
    w1=load_workbook(ROOT/'input'/'附件1.xlsx',data_only=True)
    rows=list(w1.active.values); a=np.asarray([r[1:4] for r in rows[1:]],float)
    assert [_minute(r[0]) for r in rows[1:]]==list(range(10,1441,10))
    def matrix(file,sheet=None):
        w=load_workbook(ROOT/'input'/file,data_only=True);s=w[sheet] if sheet else w.active
        r=list(s.values)
        assert [_minute(x) for x in r[0][1:]]==list(range(10,1441,10))
        assert list(pd.to_datetime([x[0] for x in r[1:]]))==list(DATES)
        return np.asarray([x[1:] for x in r[1:]],float)
    L=matrix('附件2.xlsx','小区负载');PV=matrix('附件2.xlsx','光伏发电实际功率');P=matrix('附件4.xlsx')
    w3=load_workbook(ROOT/'input'/'附件3.xlsx',data_only=True)
    F=np.full((365,4,24),np.nan);mapping=[];seen=set();last=None
    for row in list(w3.active.values)[1:]:
        if row[0] not in [None,'']:last=pd.Timestamp(row[0])
        hour=int(str(row[1]).split(':')[0]); day=(last-DATES[0]).days;assert hour in [0,6,12,18]
        assert (day,hour) not in seen;seen.add((day,hour));F[day,hour//6]=row[2:26]
        for k in range(24):mapping.append([str(last+pd.Timedelta(hours=hour)),k+1,str(last+pd.Timedelta(hours=hour+k+1))])
    assert len(seen)==1460
    pd.DataFrame(mapping,columns=['发布时间','预报第几小时','目标时间']).to_csv(ROOT/'audit'/'预报时间映射.csv',index=False,encoding='utf-8-sig')
    stats=[]
    for name,v,unit in [('附件1电价',a[:,0],'元/kWh'),('附件1负载',a[:,1],'kW'),('附件1光伏',a[:,2],'kW'),('附件2负载',L,'kW'),('附件2光伏',PV,'kW'),('附件3预报',F,'kW'),('附件4电价',P,'元/kWh')]:
        stats.append(dict(数据=name,形状=str(v.shape),单位=unit,数量=v.size,缺失=int(np.isnan(v).sum()),非有限=int((~np.isfinite(v)).sum()),负值=int((v<0).sum()),最小=float(v.min()),最大=float(v.max()),均值=float(v.mean())))
        assert np.isfinite(v).all() and (v>=0).all(),name
    pd.DataFrame(stats).to_csv(ROOT/'audit'/'数据审计.csv',index=False,encoding='utf-8-sig')
    manifest={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in (ROOT/'input').iterdir()}
    dump(manifest,ROOT/'audit'/'输入SHA256.json')
    tm=[];templates={}
    for f in (ROOT/'input').glob('result*.xlsx'):
        w=load_workbook(f);s=w['计划购电量'];labels=[s.cell(i,1).value for i in range(2,146)] if f.stem=='result1' else [s.cell(1,j).value for j in range(2,146)]
        ids=[align_time(x) for x in labels];assert sorted(ids)==list(range(144))
        for i,(label,t) in enumerate(zip(labels,ids)):tm.append([f.name,i+1,label,interval(t),time_label(t+1),t,'原末列解释' if t==0 else '按左端匹配'])
        templates[f.name]={s.title:[s.max_row,s.max_column] for s in w}
    pd.DataFrame(tm,columns=['文件','数据序号','原模板标签','规范区间','附件右端采样时刻','内部索引','说明']).to_csv(ROOT/'audit'/'模板逐列时间映射.csv',index=False,encoding='utf-8-sig')
    dump(templates,ROOT/'audit'/'模板结构.json')
    np.savez_compressed(ROOT/'results'/'data.npz',a=a,L=L,PV=PV,P=P,F=F)
    return dict(a=a,L=L,PV=PV,P=P,F=F)
