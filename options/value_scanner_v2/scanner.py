"""Conservative EOD diagnostics; never produces executable trade signals."""
from __future__ import annotations
import argparse, hashlib, io, json, math, re, sys
from dataclasses import asdict, dataclass
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.special import ndtr

PATTERN=re.compile(r'^([A-Za-z]+\d{3,4}(?:MS)?)-?([CP])-?(\d+(?:\.\d+)?)$')
@dataclass(frozen=True)
class Config:
    min_volume:int=10
    min_open_interest:int=20
    min_peers:int=8
    max_peers:int=12
    min_each_side:int=2
    uncertainty_floor:float=.005
    min_iv_gap:float=.02
    uncertainty_multiple:float=2.
    tree_steps:int=300

def numeric(value):
    try:
        v=float(str(value).replace(',','').strip())
        return v if math.isfinite(v) else np.nan
    except (ValueError,TypeError):return np.nan

def parse_contract(contract):
    m=PATTERN.fullmatch(str(contract).strip())
    return (m[1],m[2],float(m[3])) if m else None

def black76(future,strike,t,rate,sigma,right):
    if not (future>0 and strike>0 and t>0 and sigma>0):raise ValueError('positive F,K,T,sigma required')
    s=sigma*math.sqrt(t);d1=math.log(future/strike)/s+s/2;d2=d1-s;sign=1 if right=='C' else -1
    return math.exp(-rate*t)*sign*(future*ndtr(sign*d1)-strike*ndtr(sign*d2))

def _american_tree(future,strike,t,rate,sigma,right,steps=300):
    """CRR American option on futures: zero futures drift, discount at r; premium-style."""
    if not (future>0 and strike>0 and t>0 and sigma>0 and steps>=2):raise ValueError('invalid model input')
    dt=t/steps;u=math.exp(sigma*math.sqrt(dt));d=1/u;p=(1-d)/(u-d);disc=math.exp(-rate*dt)
    sign=1 if right=='C' else -1
    f=future*np.exp((2*np.arange(steps+1)-steps)*math.log(u))
    values=np.maximum(sign*(f-strike),0)
    for n in range(steps-1,-1,-1):
        values=disc*((1-p)*values[:-1]+p*values[1:])
        f=future*np.exp((2*np.arange(n+1)-n)*math.log(u))
        values=np.maximum(values,np.maximum(sign*(f-strike),0))
    return float(values[0])

def american76(future,strike,t,rate,sigma,right,steps=300):
    return .5*(_american_tree(future,strike,t,rate,sigma,right,steps)+_american_tree(future,strike,t,rate,sigma,right,steps+1))

def model_price(f,k,t,r,v,right,style,steps=300):
    if right not in ['C','P'] or style not in ['American','European']:raise ValueError('unknown right/style')
    return american76(f,k,t,r,v,right,steps) if style=='American' else black76(f,k,t,r,v,right)

def implied_vol(price,future,strike,t,rate,right,style='European',steps=300):
    sign=1 if right=='C' else -1
    low=max(sign*(future-strike),0)*(1 if style=='American' else math.exp(-rate*t))
    high=(future if right=='C' else strike)*max(1,math.exp(-rate*t))
    if not low<price<high:return np.nan
    try:return brentq(lambda v:model_price(future,strike,t,rate,v,right,style,steps)-price,1e-5,3,xtol=1e-7)
    except ValueError:return np.nan

def load_snapshot(folder,date):
    rows=[];manifest=[]
    sources=[('SHFE_INE','raw_12c9627bd98c.txt'),('CZCE','raw_f379d002a308.txt'),('GFEX','raw_97481a6cf309.txt')]
    requests=[json.loads(x) for x in (folder/'requests.jsonl').read_text().splitlines() if x]
    for exchange,filename in sources:
        raw=(folder/filename).read_bytes();text=raw.decode('utf-8');timestamp=None
        req=next((r for r in requests if r.get('raw_file')==filename),{})
        manifest.append({'exchange':exchange,'file':filename,'sha256':hashlib.sha256(raw).hexdigest(),'request':req,'bytes':len(raw)})
        if exchange=='SHFE_INE':
            data=json.loads(text)
            if str(data.get('report_date'))!=date:raise ValueError('SHFE date mismatch')
            timestamp=data.get('update_date');records=data['o_curinstrument']
            keys=dict(contract='INSTRUMENTID',close='CLOSEPRICE',settlement='SETTLEMENTPRICE',volume='VOLUME',open_interest='OPENINTEREST',delta='DELTA',underlying='UNDERLYINGINSTRID')
        elif exchange=='GFEX':
            data=json.loads(text)
            if data.get('code')!='0' or data.get('param',{}).get('trade_date')!=[date]:raise ValueError('GFEX date/status mismatch')
            records=data['data'];keys=dict(contract='delivMonth',close='close',settlement='clearPrice',volume='volumn',open_interest='openInterest',delta='delta')
        else:
            iso=f'{date[:4]}-{date[4:6]}-{date[6:]}'
            if iso not in text.splitlines()[0]:raise ValueError('CZCE date mismatch')
            table=pd.read_csv(io.StringIO(text),sep='|',skiprows=1,dtype=str);table.columns=table.columns.str.strip()
            records=table.to_dict('records');keys=dict(contract='合约代码',close='今收盘',settlement='今结算',volume='成交量(手)',open_interest='持仓量',delta='DELTA',published_iv='隐含波动率')
        for item in records:
            contract=str(item.get(keys['contract'],'')).strip();parsed=parse_contract(contract)
            if not parsed:continue
            series,right,strike=parsed
            row=dict(exchange=exchange,contract=contract,series=series,right=right,strike=strike,trade_date=date,source_file=filename,
                     publication_timestamp=timestamp,underlying=None,published_iv=np.nan)
            for col,key in keys.items():
                if col!='contract':row[col]=str(item[key]).strip().lower() if col=='underlying' else numeric(item.get(key))
            if exchange=='CZCE':row['published_iv']/=100
            row['iv_origin']='official_published_definition_unverified' if np.isfinite(row['published_iv']) else 'missing'
            rows.append(row)
    df=pd.DataFrame(rows)
    if df.duplicated(['exchange','contract']).any():raise ValueError('duplicate option contract')
    return df,manifest

def apply_metadata(df,metadata,date,futures=None,cfg=Config()):
    df=df.copy()
    for c in ['future','expiry','style','rate','metadata_source','future_date','future_source','underlying_verified','tick_size']:
        df[c]=np.nan if c in ['future','rate','tick_size'] else ''
    if futures is not None:
        if futures.contract_id.duplicated().any():raise ValueError('duplicate futures contract')
        fs=futures.set_index('contract_id')
        for i,row in df.iterrows():
            # Explicit futures/options contract naming convention, retains native CZCE year/month.
            key=row.series.lower()
            if key in fs.index:
                f=fs.loc[key]
                df.loc[i,['future','future_date','future_source','underlying_verified']]=[f.settle,str(f.trade_date),f.source,key]
    if metadata is not None:
        required={'exchange','contract','underlying_verified','future','future_date','future_source','expiry','style','rate','metadata_source'}
        if not required<=set(metadata):raise ValueError(f'missing metadata columns {required-set(metadata)}')
        if metadata.duplicated(['exchange','contract']).any():raise ValueError('duplicate metadata keys')
        known=set(zip(df.exchange,df.contract))
        if any(k not in known for k in zip(metadata.exchange,metadata.contract)):raise ValueError('unknown metadata contract')
        meta=metadata.set_index(['exchange','contract'])
        for i,row in df.iterrows():
            if (row.exchange,row.contract) in meta.index:
                m=meta.loc[(row.exchange,row.contract)]
                for c in required-{'exchange','contract'} | ({'tick_size'}&set(meta.columns)):df.at[i,c]=m[c]
    dt=pd.to_datetime(date,format='%Y%m%d')
    df['tenor_years']=(pd.to_datetime(df.expiry,errors='coerce')-dt).dt.total_seconds()/(365*86400)
    for c in ['future','rate','tick_size']:df[c]=df[c].map(numeric)
    df['future_valid']=(df.future.gt(0)&df.future_date.astype(str).eq(date)&df.future_source.fillna('').ne('')&df.underlying_verified.fillna('').ne(''))
    mismatch=(df.underlying.notna()&df.underlying_verified.ne('')&df.underlying.ne(df.underlying_verified)) | (df.underlying_verified.ne('') & df.underlying_verified.ne(df.series.str.lower()))
    df.loc[mismatch,'future_valid']=False
    df['metadata_valid']=df.future_valid&df.tenor_years.gt(0)&df.rate.notna()&df.metadata_source.fillna('').ne('')&df['style'].isin(['European','American'])
    df['otm_status']='unverified';df.loc[df.future_valid,'otm_status']='not_otm'
    otm=(df.right.eq('C')&df.strike.gt(df.future))|(df.right.eq('P')&df.strike.lt(df.future))
    df.loc[df.future_valid&otm,'otm_status']='otm'
    df['fit_iv']=df.published_iv
    # Recompute model IV only for verified contracts with sufficient daily activity.
    pricing_rows=df.loc[df.metadata_valid & df.volume.ge(cfg.min_volume) & df.open_interest.ge(cfg.min_open_interest)]
    print(f'Calibrating {len(pricing_rows)} verified active contracts',file=sys.stderr,flush=True)
    for counter,(i,row) in enumerate(pricing_rows.iterrows(),1):
        if counter%200==0:print(f'IV calibration {counter}/{len(pricing_rows)}',file=sys.stderr,flush=True)
        df.at[i,'fit_iv']=implied_vol(row.settlement,row.future,row.strike,row.tenor_years,row.rate,row.right,row['style'],cfg.tree_steps)
        df.at[i,'iv_origin']=row['style']+'_from_settlement'
    return df

def shape_flags(df):
    """Marks all legs of settlement shape inconsistencies, never executable arbitrage."""
    flags={i:set() for i in df.index}
    for _,group in df.groupby(['exchange','series','right']):
        g=group.loc[group.settlement.ge(0)].sort_values('strike')
        if g.strike.duplicated().any():
            for i in g.index:flags[i].add('duplicate_strike')
            continue
        ids=g.index.tolist();k=g.strike.to_numpy();p=g.settlement.to_numpy()
        tol=max(1e-8,float(g.tick_size.max())*2) if g.tick_size.notna().any() else 1e-8
        sign=-1 if g.right.iloc[0]=='C' else 1
        for j,change in enumerate(np.diff(p)):
            if sign*change < -tol:
                for i in ids[j:j+2]:flags[i].add('settlement_monotonicity_violation')
        for j in range(len(k)-2):
            chord=p[j]+(p[j+2]-p[j])*(k[j+1]-k[j])/(k[j+2]-k[j])
            if p[j+1]>chord+tol:
                for i in ids[j:j+3]:flags[i].add('settlement_convexity_violation')
    return flags

def robust_fit(x,y,degree):
    design=np.vander(x,degree+1,increasing=True);weights=np.ones(len(x))
    for _ in range(15):
        coef=np.linalg.lstsq(design*np.sqrt(weights[:,None]),y*np.sqrt(weights),rcond=None)[0]
        residual=y-design@coef;mad=max(float(1.4826*np.median(abs(residual-np.median(residual)))),1e-6)
        weights=np.minimum(1,1.5*mad/np.maximum(abs(residual),1e-12))
    leverage=float(np.linalg.pinv(design.T@(weights[:,None]*design))[0,0])
    return float(coef[0]),mad*math.sqrt(1+max(leverage,0)),weights

def loo_smile(strikes,vols,target,cfg=Config()):
    """Robust LOO local quadratic; 2 bracketing strikes per side; no extrapolation.
    Envelope is heuristic residual/degree sensitivity, NOT a statistical confidence interval.
    F cancels in within-series log(K/Ktarget); missing F still prohibits OTM classification.
    """
    x=np.log(np.asarray(strikes,dtype=float)/target);y=np.asarray(vols,dtype=float)
    keep=np.isfinite(x)&np.isfinite(y)&(y>0)&(y<3)&(abs(x)>1e-12);x,y=x[keep],y[keep]
    order=np.argsort(abs(x),kind='stable')[:cfg.max_peers];x,y=x[order],y[order]
    if len(x)<cfg.min_peers or (x<0).sum()<cfg.min_each_side or (x>0).sum()<cfg.min_each_side:return None
    x=x/max(float(np.max(abs(x))),1e-8)
    estimate,uncertainty,weights=robust_fit(x,y,2);linear,_,_=robust_fit(x,y,1)
    inliers=int((weights>.5).sum())
    if ((x<0)&(weights>.5)).sum()<cfg.min_each_side or ((x>0)&(weights>.5)).sum()<cfg.min_each_side:return None
    if inliers<cfg.min_peers or not 0<estimate<3:return None
    return estimate,max(cfg.uncertainty_floor,uncertainty,abs(estimate-linear)),len(x),inliers

def scan(df,cfg=Config()):
    df=df.copy();flags=shape_flags(df)
    for i,row in df.iterrows():
        for condition,label in [(not row.volume>0,'zero_or_missing_volume'),(not row.volume>=cfg.min_volume,'low_volume'),
            (not row.open_interest>=cfg.min_open_interest,'low_open_interest'),(not row.close>0,'invalid_close'),
            (not row.settlement>0,'invalid_settlement'),(not row.metadata_valid,'missing_or_invalid_contract_metadata'),
            (not np.isfinite(row.fit_iv),'missing_contract_iv'),(not np.isfinite(row.tick_size),'tick_size_unknown'),
            (np.isfinite(row.tick_size) and row.settlement<=5*row.tick_size,'near_tick_floor')]:
            if condition:flags[i].add(label)
        flags[i].update(['no_bid_ask','no_quote_timestamp','settlement_not_executable','settlement_model_circularity_possible'])
    df['peer_eligible']=df.volume.ge(cfg.min_volume)&df.open_interest.ge(cfg.min_open_interest)&df.settlement.gt(0)&df.close.gt(0)&df.fit_iv.between(.001,3,inclusive='neither')
    for i in df.index:
        if any('violation' in f or f in ['duplicate_strike','near_tick_floor'] for f in flags[i]):df.at[i,'peer_eligible']=False
    for c in ['smile_iv','iv_gap','uncertainty_envelope','gap_to_envelope','peer_count','robust_inliers','theoretical_price','conservative_theoretical_price','settlement_gap','tree_price_difference']:df[c]=np.nan
    df['diagnostic_status']='insufficient_inputs';df['relative_value_candidate']=False;df['trade_signal']=False
    for _,g in df.groupby(['exchange','series','right','iv_origin','expiry','style'],dropna=False):
        peers=g.loc[g.peer_eligible]
        for i,row in g.iterrows():
            if not row.peer_eligible:continue
            other=peers.loc[peers.index!=i];fit=loo_smile(other.strike,other.fit_iv,row.strike,cfg)
            if fit is None:flags[i].add('insufficient_bracketing_peers');continue
            estimate,envelope,n,inliers=fit;gap=estimate-row.fit_iv
            df.loc[i,['smile_iv','iv_gap','uncertainty_envelope','gap_to_envelope','peer_count','robust_inliers']]=[estimate,gap,envelope,gap/envelope,n,inliers]
            df.at[i,'diagnostic_status']='within_smile_envelope';low=gap>=max(cfg.min_iv_gap,cfg.uncertainty_multiple*envelope)
            if low:df.at[i,'diagnostic_status']='low_iv_unverified_hypothesis'
            if low and row.metadata_valid and row.otm_status=='otm' and row.tick_size>0:
                args=(row.future,row.strike,row.tenor_years,row.rate)
                price=model_price(*args,estimate,row.right,row['style'],cfg.tree_steps)
                conservative=model_price(*args,max(.001,estimate-cfg.uncertainty_multiple*envelope),row.right,row['style'],cfg.tree_steps)
                fine=model_price(*args,estimate,row.right,row['style'],cfg.tree_steps*2)
                fine_conservative=model_price(*args,max(.001,estimate-cfg.uncertainty_multiple*envelope),row.right,row['style'],cfg.tree_steps*2)
                error=max(abs(fine-price),abs(fine_conservative-conservative))
                df.loc[i,['theoretical_price','conservative_theoretical_price','settlement_gap','tree_price_difference']]=[price,conservative,conservative-row.settlement,error]
                if conservative-row.settlement>max(2*row.tick_size,3*error):
                    df.at[i,'relative_value_candidate']=True;df.at[i,'diagnostic_status']='theoretical_relative_value_only'
    df['quality_flags']=[';'.join(sorted(flags[i])) for i in df.index]
    return df

def run(input_dir,output_dir,date,metadata_path=None,futures_path=None,cfg=Config()):
    output_dir.mkdir(parents=True,exist_ok=True);df,manifest=load_snapshot(input_dir,date)
    metadata=pd.read_csv(metadata_path,dtype={'future_date':str}) if metadata_path else None
    futures=pd.read_csv(futures_path,dtype={'trade_date':str}) if futures_path else None
    result=scan(apply_metadata(df,metadata,date,futures,cfg),cfg);result.to_csv(output_dir/'diagnostics.csv',index=False)
    hypotheses=result.loc[result.diagnostic_status.eq('low_iv_unverified_hypothesis')].sort_values('gap_to_envelope',ascending=False)
    hypotheses.to_csv(output_dir/'unverified_iv_hypotheses.csv',index=False)
    candidates=result.loc[result.relative_value_candidate].sort_values('settlement_gap',ascending=False)
    candidates.to_csv(output_dir/'theoretical_relative_value_candidates.csv',index=False)
    inventory=result.groupby('exchange').agg(contracts=('contract','size'),series=('series','nunique'),published_iv_count=('published_iv','count'),
        valid_futures=('future_valid','sum'),valid_metadata=('metadata_valid','sum'),quality_peers=('peer_eligible','sum'),fitted_rows=('smile_iv','count'))
    inventory.to_csv(output_dir/'inventory.csv');baseline={}
    if (input_dir/'selected.csv').exists():
        old=pd.read_csv(input_dir/'selected.csv');old['合约名称']=old['合约名称'].str.strip();old['exchange_v2']=old.exchange.replace({'SHFE':'SHFE_INE'})
        merged=old.merge(result,left_on=['exchange_v2','合约名称'],right_on=['exchange','contract'],how='left',suffixes=('_legacy','_v2'))
        merged.to_csv(output_dir/'legacy_selection_audit.csv',index=False)
        baseline={'legacy_selected':len(old),'matched_contracts':int(merged.contract.notna().sum()),'zero_volume':int(merged.volume.eq(0).sum()),
                  'unverified_otm':int(merged.otm_status.eq('unverified').sum()),'not_otm':int(merged.otm_status.eq('not_otm').sum()),
                  'new_theoretical_candidates':int(merged.relative_value_candidate.eq(True).sum())}
    summary={'date':date,'config':asdict(cfg),'contracts':len(result),'published_contract_iv':int(result.published_iv.notna().sum()),
        'valid_futures':int(result.future_valid.sum()),'verified_otm':int(result.otm_status.eq('otm').sum()),'valid_metadata':int(result.metadata_valid.sum()),
        'fitted_contracts':int(result.smile_iv.notna().sum()),'unverified_iv_hypotheses':len(hypotheses),'theoretical_relative_value_candidates':len(candidates),
        'executable_trade_signals':0,'zero_volume':int(result.volume.eq(0).sum()),'baseline_comparison':baseline,
        'missing_exchange':'DCE original official request HTTP 412; not zero opportunities',
        'interpretation':'EOD diagnostics only; settlement circularity possible. No expected returns, win probabilities or Kelly.'}
    (output_dir/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    provenance={'inputs':manifest,'source_code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    for label,path in [('metadata',metadata_path),('futures',futures_path)]:
        provenance[label]={'file':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()} if path else None
    (output_dir/'manifest.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+'\n');print(json.dumps(summary,ensure_ascii=False,indent=2))
    return result,summary

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['input','output']:parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--date',required=True);parser.add_argument('--metadata',type=Path);parser.add_argument('--futures',type=Path)
    a=parser.parse_args()
    if not re.fullmatch(r'\d{8}',a.date):parser.error('--date must be YYYYMMDD')
    run(a.input,a.output,a.date,a.metadata,a.futures)
if __name__=='__main__':main()
