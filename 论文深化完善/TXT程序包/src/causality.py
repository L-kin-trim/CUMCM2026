from model import *
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
if __name__=='__main__':causality()
