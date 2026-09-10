"""在原工作簿上填写，逐列回读核算；制作结果表与因果性测试。"""
from model import *
from copy import copy

def extend_storage(ws,out):
    styles=[[copy(ws.cell(2+i,j)._style) for j in range(1,7)] for i in range(6)]
    for row in ws:
        if row[0].row>1:
            for c in row:c.value=None
    for d in range(31,365):
        r=2+(d-31)*6
        for k in range(6):
            for j in range(1,7):ws.cell(r+k,j)._style=copy(styles[k][j-1])
            ws.cell(r+k,2,f'{k*4}:00-{(k+1)*4}:00')
            ws.cell(r+k,3,float(out['C'][d,k*24:(k+1)*24].sum()))
            ws.cell(r+k,4,float(out['D'][d,k*24:(k+1)*24].sum()))
        ws.cell(r,1,DATES[d].to_pydatetime());ws.cell(r,5,dt.time(0,0));ws.cell(r+1,5,'24:00')
        ws.cell(r,6,float(out['S'][d,0]));ws.cell(r+1,6,float(out['S'][d,-1]))
def extend_emergency(ws,out):
    styles=[[copy(ws.cell(2+i,j)._style) for j in range(1,4)] for i in range(3)]
    for row in ws:
        if row[0].row>1:
            for c in row:c.value=None
    r=2
    for d in range(31,365):
        events=merge_emergency_intervals(out['R'][d]);n=max(3,len(events))
        for k in range(n):
            for j in range(1,4):ws.cell(r+k,j)._style=copy(styles[min(k,2)][j-1])
        ws.cell(r,1,DATES[d].to_pydatetime())
        if not events:ws.cell(r,2,'无');ws.cell(r,3,0.)
        for k,(label,amount) in enumerate(events):ws.cell(r+k,2,label);ws.cell(r+k,3,amount)
        r+=n

def export():
    data=load_data();checks=[]
    q1=np.load(ROOT/'results'/'q1.npz');w=load_workbook(ROOT/'input'/'result1.xlsx');s=w['计划购电量']
    for r in range(2,146):s.cell(r,2,float(q1['G'][align_time(s.cell(r,1).value)]))
    s=w['充放电量']
    for k in range(6):s.cell(k+2,2,float(q1['C'][k*24:(k+1)*24].sum()));s.cell(k+2,3,float(q1['D'][k*24:(k+1)*24].sum()))
    s.cell(2,5,float(q1['S'][0]));s.cell(3,5,float(q1['S'][-1]));w.save(ROOT/'result1_final.xlsx')
    for filename,tag in [('result2','q2'),('result3','q3_D'),('result4-2','q42'),('result4-3','q43_D')]:
        o=dict(np.load(ROOT/'results'/f'{tag}.npz'));df=pd.read_csv(ROOT/'results'/f'{tag}_daily.csv');w=load_workbook(ROOT/'input'/f'{filename}.xlsx')
        for name,key in [('计划购电量','G0'),('调整购电量','G')]:
            if name not in w:continue
            s=w[name];ids=[align_time(s.cell(1,j).value) for j in range(2,146)]
            for r,d in enumerate(range(31,365),2):
                assert pd.Timestamp(s.cell(r,1).value)==DATES[d]
                for j,t in enumerate(ids,2):s.cell(r,j,float(o[key][d,t]))
                s.cell(r,146,float(o[key][d].sum()))
                s.cell(r,147,float(df.base.iloc[d] if key=='G0' else df.base.iloc[d]+df.adjustment.iloc[d]))
        extend_storage(w['充放电量'],o);extend_emergency(w['紧急购电量'],o)
        w.save(ROOT/f'{filename}_final.xlsx')
    # 独立重新读取每一份文件；重新计算所填数值和费用，不依赖Excel缓存。
    for f in sorted(ROOT.glob('result*_final.xlsx')):
        name=f.stem.replace('_final','');orig=load_workbook(ROOT/'input'/f'{name}.xlsx');w=load_workbook(f,data_only=True)
        assert w.sheetnames==orig.sheetnames
        for sn in w.sheetnames:
            assert [c.value for c in w[sn][1]]==[c.value for c in orig[sn][1]]
        maxerr=0.
        if name=='result1':
            for r in range(2,146):
                assert w['计划购电量'].cell(r,1).value==orig['计划购电量'].cell(r,1).value
                t=align_time(w['计划购电量'].cell(r,1).value);maxerr=max(maxerr,abs(w['计划购电量'].cell(r,2).value-q1['G'][t]))
        else:
            tag={'result2':'q2','result3':'q3_D','result4-2':'q42','result4-3':'q43_D'}[name];o=np.load(ROOT/'results'/f'{tag}.npz')
            for sn,key in [('计划购电量','G0'),('调整购电量','G')]:
                if sn not in w:continue
                s=w[sn];ids=[align_time(s.cell(1,j).value) for j in range(2,146)]
                for r,d in enumerate(range(31,365),2):
                    assert s.cell(r,1).value==orig[sn].cell(r,1).value
                    v=np.array([s.cell(r,j).value for j in range(2,146)],float);assert np.isfinite(v).all() and v.min()>=0
                    p=data['P'][d] if name.startswith('result4') else data['a'][:,0]
                    cost=p@o[key][d]
                    if key=='G':cost+=.5*p@(o['plus'][d]+o['minus'][d])
                    maxerr=max(maxerr,np.max(np.abs(v-o[key][d,ids])),abs(v.sum()-s.cell(r,146).value),abs(cost-s.cell(r,147).value))
            s=w['充放电量']
            for d in range(31,365):
                r=2+(d-31)*6;assert pd.Timestamp(s.cell(r,1).value)==DATES[d]
                for k in range(6):
                    maxerr=max(maxerr,abs(s.cell(r+k,3).value-o['C'][d,24*k:24*k+24].sum()),abs(s.cell(r+k,4).value-o['D'][d,24*k:24*k+24].sum()))
                maxerr=max(maxerr,abs(s.cell(r,6).value-o['S'][d,0]),abs(s.cell(r+1,6).value-o['S'][d,-1]))
            s=w['紧急购电量'];sums={};last=None
            for row in list(s.values)[1:]:
                if row[0] is not None:last=pd.Timestamp(row[0]);sums[last]=0.
                if isinstance(row[2],(float,int)):sums[last]+=row[2]
            for d in range(31,365):maxerr=max(maxerr,abs(sums[DATES[d]]-o['R'][d].sum()))
        # 样式、列宽、表头及预置日期语义保持；省略行按日展开是明确的模板扩展。
        for sn in orig.sheetnames:
            keys=set(orig[sn].column_dimensions)|set(w[sn].column_dimensions)
            for key in keys:
                a=orig[sn].column_dimensions[key];b=w[sn].column_dimensions[key]
                assert (a.width,a.hidden,a.bestFit,a.outlineLevel)==(b.width,b.hidden,b.bestFit,b.outlineLevel)
            for c in orig[sn][1]:assert c._style==w[sn].cell(c.row,c.column)._style
        checks.append(dict(文件=f.name,最大差=float(maxerr),状态='PASS' if maxerr<1e-6 else 'FAIL'))
    assert all(c['状态']=='PASS' for c in checks)
    pd.DataFrame(checks).to_csv(ROOT/'audit'/'Excel回读验证.csv',index=False,encoding='utf-8-sig')
    # 完整表1--3：四典型日 × 四年度模型，保留每一个紧急事件。
    t1=[];t2=[];t3=[]
    for tag in ['q2','q3_D','q42','q43_D']:
        o=np.load(ROOT/'results'/f'{tag}.npz');df=pd.read_csv(ROOT/'results'/f'{tag}_daily.csv')
        for d in [78,171,265,354]:
            for t in [60,72,84,96,108,120]:t1.append(dict(模型=tag,日期=str(DATES[d].date()),时间段=interval(t),日前购电量=o['G0'][d,t],最终常规购电量=o['G'][d,t]))
            for k in range(6):t2.append(dict(模型=tag,日期=str(DATES[d].date()),时间段=interval(24*k,24*k+24),充电量=o['C'][d,24*k:24*k+24].sum(),放电量=o['D'][d,24*k:24*k+24].sum(),日初SOC=o['S'][d,0],日末SOC=o['S'][d,-1]))
            for label,amount in merge_emergency_intervals(o['R'][d]) or [('无',0)]:t3.append(dict(模型=tag,日期=str(DATES[d].date()),时间段=label,紧急购电量=amount))
    for i,rows in enumerate([t1,t2,t3],1):pd.DataFrame(rows).to_csv(ROOT/'results'/f'表{i}_典型日.csv',index=False,encoding='utf-8-sig')
    print(checks)

def causality():
    data=load_data();f=np.load(ROOT/'results'/'forecasts.npz');sel=json.loads((ROOT/'results'/'selected.json').read_text(encoding='utf-8'));checks=[]
    for m in METHODS:
        for key,col in [('L',1),('PV',2)]:
            for d in [31,78,171,265,354]:
                altered=data[key].copy();altered[d:]=1e9
                err=np.max(np.abs(forecast(data[key],d,m,data['a'][:,col])-forecast(altered,d,m,data['a'][:,col])))
                checks.append(dict(检查=f'{m}/{key}/d={d}未来污染',误差=err,状态='PASS' if err==0 else 'FAIL'))
    fl=f[sel['method']+'_L'].copy();fp=f[sel['method']+'_PV'].copy();fl[:31]=f['ewma_L'][:31];fp[:31]=f['ewma_PV'][:31]
    opts=dict(days=[78],q3=True,updates=(6,12,18),margin=sel['margin'],terminal=sel['terminal'],save=False)
    o,_=run_policy(data,fl,fp,**opts)
    alt={k:v.copy() for k,v in data.items()};alt['L'][78,72:]*=1.7;alt['PV'][78,72:]*=.3;alt['F'][78,2:]*=1.5
    b,_=run_policy(alt,fl,fp,**opts)
    err=max(np.max(np.abs(o['G0']-b['G0'])),np.max(np.abs(o['G'][:,:72]-b['G'][:,:72])),np.max(np.abs(o['S'][:,:73]-b['S'][:,:73])))
    checks.append(dict(检查='12时后实际值和预报污染不改变此前计划与状态',误差=err,状态='PASS' if err<1e-6 else 'FAIL'))
    assert all(x['状态']=='PASS' for x in checks)
    pd.DataFrame(checks).to_csv(ROOT/'audit'/'因果性污染测试.csv',index=False,encoding='utf-8-sig')
    dump(dict(selection_cutoff='2025-01-31 24:00',evaluation_start='2025-02-01 00:00',history_rule='strictly before day d, endpoint at day d 00:00 permitted',Jan_policy='EWMA, margin .5, terminal .5; not retrospectively changed',price_assumption='Q4 main: known day curve; causal extensions separate',template_last_column='user-approved erratum: current day 00:00-00:10'),ROOT/'audit'/'信息集.json')
    print('causality PASS',len(checks))

if __name__=='__main__':
    export();causality()
