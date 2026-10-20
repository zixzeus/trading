"""Join independently fetched official files; explicit rate scenario, never infer expiry."""
import argparse,json,re
from pathlib import Path
import pandas as pd

def main():
    p=argparse.ArgumentParser();p.add_argument('--folder',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--rate',type=float,default=.02);a=p.parse_args()
    expiry=pd.read_csv(a.folder/'shfe_ine_option_expiry_20261019.csv',dtype={'expiry':str,'trade_date':str})
    f=pd.read_csv(a.folder/'underlying_futures_20261019.csv',dtype={'trade_date':str}).set_index('contract_id')
    styles=json.loads((a.folder/'american_style_sources.json').read_text());rows=[]
    for _,e in expiry.iterrows():
        if e.underlying_id not in f.index:continue
        u=f.loc[e.underlying_id];product=re.match('[a-z]+',e.underlying_id)[0]
        if product not in styles:continue
        if e.trade_date!=u.trade_date:raise ValueError('futures/contract metadata date mismatch')
        rows.append(dict(exchange='SHFE_INE',contract=e.official_contract_id,underlying_verified=e.underlying_id,
          future=u.settle,future_date=u.trade_date,future_source=u.source,expiry=pd.to_datetime(e.expiry,format='%Y%m%d').strftime('%Y-%m-%d'),
          style='American',rate=a.rate,rate_source='explicit_scenario_assumption_not_observed',metadata_source=e.source,
          tick_size=e.tick,style_source=styles[product],multiplier=e.multiplier))
    out=pd.DataFrame(rows);out.to_csv(a.output,index=False);print(f'{len(out)} exact-expiry official contracts prepared')
if __name__=='__main__':main()
