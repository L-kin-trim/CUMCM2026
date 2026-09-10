"""独立回读原始Excel，与复现轨迹比较；不写入任何原始文件。"""
from model import *

def main():
    project=ROOT.parents[1]; data=load_data();checks=[];typical=[];events=[];blocks=[]
    q1=np.load(ROOT/'results/q1.npz')
    mapping={'result1_final.xlsx':'q1','result2_final.xlsx':'q2','result3_final.xlsx':'q3_D',
             'result4-2_final.xlsx':'q42','result4-3_final.xlsx':'q43_D'}
    payload={}
    for fname,tag in mapping.items():
        wb=load_workbook(project/fname,data_only=True)
        o=dict(np.load(ROOT/'results'/f'{tag}.npz'));err=0.;counts=0
        if tag=='q1':
            for row in list(wb['计划购电量'].values)[1:]:
                err=max(err,abs(row[1]-o['G'][align_time(row[0])]))
                counts+=1
            for k in range(6):
                row=list(wb['充放电量'].values)[k+1]
                err=max(err,abs(row[1]-o['C'][k*24:(k+1)*24].sum()),abs(row[2]-o['D'][k*24:(k+1)*24].sum()))
            payload[tag]={k:v.tolist() for k,v in o.items()}
        else:
            df=pd.read_csv(ROOT/'results'/f'{tag}_daily.csv')
            for sn,key in [('计划购电量','G0'),('调整购电量','G')]:
                if sn not in wb:continue
                rows=list(wb[sn].values);ids=[align_time(x) for x in rows[0][1:145]]
                assert sorted(ids)==list(range(144)) and len(rows)==335
                for i,row in enumerate(rows[1:],31):
                    assert pd.Timestamp(row[0])==DATES[i]
                    vals=np.asarray(row[1:145],float);assert np.isfinite(vals).all() and vals.min()>=-1e-7
                    money=df.base.iloc[i]+(df.adjustment.iloc[i] if key=='G' else 0)
                    err=max(err,np.max(np.abs(vals-o[key][i,ids])),abs(sum(vals)-row[145]),abs(money-row[146]));counts+=144
            s=wb['充放电量']
            for d in range(31,365):
                r=2+(d-31)*6
                assert pd.Timestamp(s.cell(r,1).value)==DATES[d]
                for k in range(6):
                    err=max(err,abs(s.cell(r+k,3).value-o['C'][d,k*24:(k+1)*24].sum()),abs(s.cell(r+k,4).value-o['D'][d,k*24:(k+1)*24].sum()))
                err=max(err,abs(s.cell(r,6).value-o['S'][d,0]),abs(s.cell(r+1,6).value-o['S'][d,-1]))
            got={};last=None
            for row in list(wb['紧急购电量'].values)[1:]:
                if row[0] is not None:last=pd.Timestamp(row[0]);got[last]=[]
                if row[1] is not None and isinstance(row[2],(int,float)):got[last].append((row[1],row[2]))
            for d in range(31,365):
                expected=merge_emergency_intervals(o['R'][d]) or [('无',0)]
                assert [x[0] for x in got[DATES[d]]]==[x[0] for x in expected]
                err=max(err,max(abs(a[1]-b[1]) for a,b in zip(got[DATES[d]],expected)))
            for d in [78,171,265,354]:
                rec=dict(model=tag,date=str(DATES[d].date()),**{k:float(df[k].iloc[d]) for k in ['G0','G','base','adjustment','emergency','total','R']})
                rec['initial']=float(o['S'][d,0]);rec['final']=float(o['S'][d,-1])
                rec['slots']=[{'time':interval(t),'plan':float(o['G0'][d,t]),'final':float(o['G'][d,t])} for t in [60,72,84,96,108,120]]
                rec['blocks']=[{'time':interval(k*24,(k+1)*24),'charge':float(o['C'][d,k*24:(k+1)*24].sum()),'discharge':float(o['D'][d,k*24:(k+1)*24].sum())} for k in range(6)]
                rec['events']=merge_emergency_intervals(o['R'][d]) or [('无',0.)]
                typical.append(rec)
            payload[tag]={'daily':df.iloc[31:].to_dict('records')}
        checks.append(dict(file=fname,compared_interval_values=counts,max_abs_difference=float(err),result='一致' if err<1e-5 else '需核查'))
    dump(checks,ROOT/'audit/原始Excel独立复算.json')
    dump(typical,ROOT/'results/指定日期完整结果.json')
    dump(payload,ROOT/'results/工作簿修订数据.json')
    assert all(x['max_abs_difference']<1e-5 for x in checks),checks
    print(json.dumps(checks,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
