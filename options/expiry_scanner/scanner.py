"""Expiry research, with explicit trading calendars and fail-closed live inputs.
All thresholds are unvalidated, configurable heuristics. Never submits orders.
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
import json
import math
import re
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
from options.value_scanner_v2.scanner import load_snapshot

TZ = ZoneInfo('Asia/Shanghai')

@dataclass(frozen=True)
class Config:
    min_eod_volume: int = 100
    min_eod_oi: int = 100
    max_moneyness: float = .03
    max_near_days: int = 5
    max_age_seconds: float = 3
    max_quote_skew_seconds: float = 1
    max_relative_spread: float = .08
    min_depth: int = 5
    min_live_volume: int = 100
    min_live_oi: int = 100
    max_slippage_ticks: int = 1
    breakout_buffer_ticks: int = 2
    max_chase_fraction: float = .003
    min_relative_volume: float = 1.5
    exit_buffer_minutes: int = 30
    entry_cutoff_minutes: int = 60
    max_loss_fraction: float = .0025
    max_daily_loss_fraction: float = .01
    max_total_premium_fraction: float = .01
    max_premium_fraction_underlying: float = .015


    def __post_init__(self):
        for k,v in asdict(self).items():
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0:
                raise ValueError('config values must be finite and positive: '+k)
        for k in ['max_moneyness','max_relative_spread','max_chase_fraction','max_loss_fraction','max_daily_loss_fraction','max_total_premium_fraction','max_premium_fraction_underlying']:
            if getattr(self,k)>=1: raise ValueError('fraction must be below 1: '+k)
        if self.entry_cutoff_minutes<self.exit_buffer_minutes: raise ValueError('entry cutoff must precede exit buffer')


def aware(value):
    result = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if result.tzinfo is None: raise ValueError('timezone offset required')
    return result.astimezone(TZ)


def calendar_load(path):
    c = json.loads(Path(path).read_text())
    if not c.get('source') or not c.get('verified'): raise ValueError('verified calendar source required')
    start, end = date.fromisoformat(c['start']), date.fromisoformat(c['end'])
    days = {date.fromisoformat(d) for d in c['trading_days']}
    if start > end or not days or any(d < start or d > end for d in days): raise ValueError('invalid calendar range')
    return c


def classify(expiry, now, calendar, max_near=5):
    """Trading days in (local calendar date, expiry]; night trading_day never changes expiry."""
    if not expiry or pd.isna(expiry): return 'unknown_expiry', None
    ex = date.fromisoformat(str(expiry)); today = now.astimezone(TZ).date()
    if ex < today: return 'expired', -1
    start, end = date.fromisoformat(calendar['start']), date.fromisoformat(calendar['end'])
    if not start <= today <= ex <= end: return 'calendar_out_of_range', None
    days = {date.fromisoformat(d) for d in calendar['trading_days']}
    if ex not in days: return 'expiry_not_trading_day', None
    n = sum(today < d <= ex for d in days)
    if ex == today:
        if now.astimezone(TZ).hour>=15: return 'expired_today_after_trading_cutoff', 0
        return '0DTE', 0
    # Non-trading local dates remain watchlist, never a false 0DTE.
    return ('near_1_5_trading_days' if 1 <= n <= max_near else 'later'), n


def screen(raw, metadata, now, calendar, cfg=Config()):
    keys = ['exchange', 'contract']
    if metadata.duplicated(keys).any(): raise ValueError('duplicate metadata')
    if raw.duplicated(keys).any(): raise ValueError('duplicate quote')
    cols = keys + ['expiry','underlying_verified','future','future_date','future_source','metadata_source','tick_size','multiplier','style']
    df = raw.merge(metadata[cols], on=keys, how='left', validate='one_to_one')
    classes = [classify(e, now, calendar, cfg.max_near_days) for e in df.expiry]
    df['expiry_bucket'] = [x[0] for x in classes]; df['trading_days_to_expiry'] = [x[1] for x in classes]
    df['moneyness_distance'] = abs(df.strike / df.future - 1)
    df['eod_eligible'] = (df.expiry_bucket.isin(['0DTE','near_1_5_trading_days']) &
        (df.volume >= cfg.min_eod_volume) & (df.open_interest >= cfg.min_eod_oi) &
        (df.moneyness_distance <= cfg.max_moneyness) & (df.close > 0) & (df.future > 0) &
        (df.future_date.astype(str) == df.trade_date.astype(str)) &
        (df.underlying_verified.str.lower() == df.series.str.lower()) &
        (df.tick_size > 0) & (df.multiplier > 0) &
        df[['future','tick_size','multiplier']].map(math.isfinite).all(axis=1) &
        df.metadata_source.notna() & df.future_source.notna())
    df['status'] = 'EOD_WATCHLIST_ONLY_NO_LIVE_QUOTES'
    # Liquidity proxy, not expected profit; never compare premiums across multipliers.
    df['liquidity_proxy'] = df[['volume','open_interest']].min(axis=1)
    watch = df[df.eod_eligible].sort_values(['trading_days_to_expiry','liquidity_proxy','moneyness_distance'], ascending=[True,False,True])
    return df, watch


def evaluate_live(record, now, calendar, cfg=Config()):
    """Evaluate one long-option breakout hypothesis. Returns research-only status.
    Full schema/example in example_live.json. Missing/invalid fields block evaluation.
    No short-leg order is produced; debit spreads require a separate atomic execution system.
    """
    rejected = lambda *why: {'status':'BLOCKED','reasons':list(why),'order':None}
    try:
        r=record
        required = ['exchange','previous_bar_end','bar_seconds','contract','underlying','right','strike','expiry','metadata_source','style','trading_day',
            'session_start','session_end','last_trade_at','broker_exercise_cutoff','flatten_by',
            'quote_timestamp','future_timestamp','bar_end','range_end','bid','ask','bid_size','ask_size',
            'future_bid','future_ask','future_bid_size','future_ask_size','option_tick','future_tick','multiplier',
            'option_lower_limit','option_upper_limit','future_lower_limit','future_upper_limit',
            'volume','open_interest','range_high','range_low','confirmed_close','previous_close',
            'relative_volume','equity','daily_loss','open_premium_risk','risk_budget','quantity','fees_roundtrip',
            'max_exit_slippage_ticks','session_verified','broker_rules_verified','flat_position_verified','options_permission_verified','exercise_risk_acknowledged','session_source','broker_rules_source','future_contract']
        missing=[k for k in required if k not in r]
        if missing: return rejected('missing:'+','.join(missing))
        if any(r[k] is not True for k in ['session_verified','broker_rules_verified','flat_position_verified','options_permission_verified','exercise_risk_acknowledged']): return rejected('unverified_session_broker_or_position')
        if any(not isinstance(r[k],str) for k in ['contract','underlying','future_contract','right','style','exchange']): return rejected('invalid_identity_type')
        if not r['contract'] or not r['underlying'] or not r['metadata_source'] or not r['session_source'] or not r['broker_rules_source']: return rejected('missing_identity_or_metadata')
        parsed = re.fullmatch(r'([A-Za-z]+\d{3,4})-?([CP])-?(\d+(?:\.\d+)?)',r['contract'])
        if not parsed or parsed[1].lower()!=r['underlying'].lower() or r['future_contract'].lower()!=r['underlying'].lower() or parsed[2]!=r['right'] or float(parsed[3])!=r['strike']: return rejected('contract_underlying_mismatch')
        if r['style'] not in ['American','European'] or r['right'] not in ['C','P']: return rejected('unknown_style_or_right')
        ns = ['bar_seconds','strike','bid','ask','bid_size','ask_size','future_bid','future_ask','future_bid_size','future_ask_size','option_tick','future_tick','multiplier','option_lower_limit','option_upper_limit','future_lower_limit','future_upper_limit','volume','open_interest','range_high','range_low','confirmed_close','previous_close','relative_volume','equity','daily_loss','open_premium_risk','risk_budget','quantity','fees_roundtrip','max_exit_slippage_ticks']
        if any(isinstance(r[k],bool) or not isinstance(r[k],(int,float)) or not math.isfinite(r[k]) for k in ns): return rejected('nonfinite_or_nonnumeric')
        if any(r[k] <= 0 for k in ns if k not in ['daily_loss','open_premium_risk','fees_roundtrip','max_exit_slippage_ticks','option_lower_limit']): return rejected('nonpositive_input')
        if any(r[k] < 0 for k in ['daily_loss','open_premium_risk','fees_roundtrip','max_exit_slippage_ticks','option_lower_limit']): return rejected('negative_risk_or_cost')
        for price,tick in [('bid','option_tick'),('ask','option_tick'),('future_bid','future_tick'),('future_ask','future_tick')]:
            if abs(r[price]/r[tick]-round(r[price]/r[tick]))>1e-6: return rejected('off_tick_quote')
        if r['quantity'] != int(r['quantity']): return rejected('quantity_not_integer')
        times={k:aware(r[k]) for k in ['session_start','session_end','last_trade_at','broker_exercise_cutoff','flatten_by','quote_timestamp','future_timestamp','bar_end','previous_bar_end','range_end']}
        now=aware(now.isoformat())
        if r['exchange'] not in calendar.get('exchange_scope',[]): return rejected('exchange_calendar_mismatch')
        # Daytime-only MVP: night trading-day mapping is intentionally unsupported.
        if date.fromisoformat(r['trading_day'])!=now.date(): return rejected('trading_day_mismatch')
        if any(times[k].second or times[k].microsecond for k in ['session_start','session_end']): return rejected('invalid_session_seconds')
        if times['range_end'] < times['session_start']+timedelta(minutes=5): return rejected('opening_range_too_short')
        if times['previous_bar_end']-timedelta(seconds=r['bar_seconds']) < times['range_end']: return rejected('bar_overlaps_opening_range')
        valid_sessions={('09:00','10:15'),('10:30','11:30'),('13:30','15:00')}
        if (times['session_start'].strftime('%H:%M'),times['session_end'].strftime('%H:%M')) not in valid_sessions: return rejected('unsupported_session')
        if r['bar_seconds'] not in [60,180,300]: return rejected('unsupported_bar_interval')
        if times['bar_end']-times['previous_bar_end']!=timedelta(seconds=r['bar_seconds']) or times['previous_bar_end']<=times['range_end']: return rejected('stale_or_noncontiguous_previous_bar')
        bucket, days=classify(r['expiry'],now,calendar,cfg.max_near_days)
        if bucket not in ['0DTE','near_1_5_trading_days']: return rejected(bucket)
        if date.fromisoformat(r['trading_day']) not in {date.fromisoformat(d) for d in calendar['trading_days']}: return rejected('unknown_trading_day')
        if times['last_trade_at'].strftime('%H:%M:%S')!='15:00:00' or times['broker_exercise_cutoff'].strftime('%H:%M:%S')>'15:30:00': return rejected('unsupported_exchange_deadline')
        if times['last_trade_at'].date()!=date.fromisoformat(r['expiry']): return rejected('last_trade_expiry_mismatch')
        if times['broker_exercise_cutoff'].date()!=date.fromisoformat(r['expiry']): return rejected('exercise_expiry_mismatch')
        if not (times['session_start'] <= times['range_end'] < times['bar_end'] <= now < times['session_end']): return rejected('invalid_session_or_unclosed_bar')
        if times['session_start'].date()!=now.date() or times['session_end'].date()!=now.date(): return rejected('session_must_be_contiguous_local_day_interval')
        # Caller supplies one official continuous interval, never a full day spanning breaks.
        if times['session_end']-times['session_start']>timedelta(hours=3): return rejected('session_interval_too_long')
        if now-times['bar_end'] > timedelta(seconds=cfg.max_age_seconds): return rejected('stale_signal_bar')
        if any(not 0 <= (now-times[k]).total_seconds() <= cfg.max_age_seconds for k in ['quote_timestamp','future_timestamp']): return rejected('stale_or_future_quote')
        if abs((times['quote_timestamp']-times['future_timestamp']).total_seconds()) > cfg.max_quote_skew_seconds: return rejected('quote_skew')
        final=min(times['last_trade_at'],times['broker_exercise_cutoff'],times['session_end'])
        if times['flatten_by'] > final-timedelta(minutes=cfg.exit_buffer_minutes): return rejected('unsafe_flatten_deadline')
        if now >= min(times['flatten_by'],final-timedelta(minutes=cfg.entry_cutoff_minutes)): return rejected('entry_cutoff')
        if not (0 < r['bid'] < r['ask'] and 0 < r['future_bid'] < r['future_ask']): return rejected('locked_crossed_or_empty_book')
        if min(r['bid_size'],r['ask_size'],r['future_bid_size'],r['future_ask_size']) < max(cfg.min_depth,r['quantity']): return rejected('insufficient_depth')
        if r['volume'] < cfg.min_live_volume or r['open_interest'] < cfg.min_live_oi: return rejected('insufficient_liquidity')
        mid=(r['bid']+r['ask'])/2; f=(r['future_bid']+r['future_ask'])/2
        if (r['ask']-r['bid'])/mid > cfg.max_relative_spread: return rejected('wide_spread')
        if not (r['option_lower_limit']+r['option_tick'] < r['bid'] < r['ask'] < r['option_upper_limit']-r['option_tick'] and r['future_lower_limit']+r['future_tick'] < r['future_bid'] < r['future_ask'] < r['future_upper_limit']-r['future_tick']): return rejected('at_or_near_price_limit')
        if abs(r['strike']/f-1) > cfg.max_moneyness: return rejected('not_near_atm')
        if r['ask']/f > cfg.max_premium_fraction_underlying: return rejected('premium_cap')
        if not r['range_low'] < r['range_high']: return rejected('invalid_range')
        buffer=cfg.breakout_buffer_ticks*r['future_tick']
        if r['right']=='C': trigger=r['range_high']+buffer; signal=r['previous_close']>trigger and r['confirmed_close']>trigger and f>trigger
        else: trigger=r['range_low']-buffer; signal=r['previous_close']<trigger and r['confirmed_close']<trigger and f<trigger
        if not signal or r['relative_volume'] < cfg.min_relative_volume: return rejected('no_confirmed_breakout')
        if abs(f/trigger-1)>cfg.max_chase_fraction: return rejected('do_not_chase')
        if r['max_exit_slippage_ticks']>cfg.max_slippage_ticks: return rejected('exit_slippage_cap')
        limit_price=r['ask']  # never an unbounded market order
        worst_loss=limit_price*r['multiplier']*r['quantity']+r['fees_roundtrip']
        if worst_loss>min(r['risk_budget'],cfg.max_loss_fraction*r['equity']): return rejected('risk_budget')
        if r['daily_loss']+worst_loss>cfg.max_daily_loss_fraction*r['equity']: return rejected('daily_loss_cap')
        if r['open_premium_risk']+worst_loss>cfg.max_total_premium_fraction*r['equity']: return rejected('portfolio_premium_cap')
        return {'status':'RESEARCH_TRIGGER_ONLY','strategy':'long_call_breakout' if r['right']=='C' else 'long_put_breakdown','contract':r['contract'],'expiry_bucket':bucket,'trading_days_to_expiry':days,'limit_price_ceiling':limit_price,'quantity':r['quantity'],'max_premium_loss_plus_fees':worst_loss,'flatten_by':times['flatten_by'].isoformat(),'underlying_invalidation':r['range_high'] if r['right']=='C' else r['range_low'],'order':None,'warning':'Not validated for profitability; exit fills and stop losses are not guaranteed. Exercise can create futures exposure.'}
    except (ValueError,TypeError,KeyError,OverflowError) as exc:
        return rejected('invalid_input:'+str(exc))


def main():
    p=argparse.ArgumentParser();p.add_argument('--raw',type=Path);p.add_argument('--metadata',type=Path);p.add_argument('--snapshot-date');p.add_argument('--asof',required=True);p.add_argument('--calendar',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--live-json',type=Path);p.add_argument('--config',type=Path)
    a=p.parse_args(); now=aware(a.asof);cal=calendar_load(a.calendar);cfg=Config(**json.loads(a.config.read_text())) if a.config else Config();a.out.mkdir(parents=True,exist_ok=True)
    if a.live_json:
        result=evaluate_live(json.loads(a.live_json.read_text()),now,cal,cfg);(a.out/'live_result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False));return
    if not all([a.raw,a.metadata,a.snapshot_date]): p.error('EOD mode requires raw metadata snapshot-date')
    if datetime.strptime(a.snapshot_date,'%Y%m%d').date()>=now.date(): raise ValueError('EOD snapshot must be a previous completed local calendar day')
    raw,manifest=load_snapshot(a.raw,a.snapshot_date);metadata=pd.read_csv(a.metadata,dtype={'future_date':str});all_rows,watch=screen(raw,metadata,now,cal,cfg)
    all_rows.to_csv(a.out/'all_contracts.csv',index=False);watch.to_csv(a.out/'watchlist.csv',index=False)
    picks=watch.groupby(['underlying_verified','right'],sort=False).head(1);picks.to_csv(a.out/'one_per_underlying_right.csv',index=False)
    summary={'asof':now.isoformat(),'snapshot_date':a.snapshot_date,'scope':'full supported raw SHFE_INE/CZCE/GFEX, not original sector filter; DCE unavailable','raw_contracts':len(raw),'verified_expiry_contracts':int(all_rows.expiry.notna().sum()),'expiry_buckets':all_rows.expiry_bucket.value_counts().to_dict(),'watchlist_contracts':len(watch),'live_triggers':0,'live_status':'BLOCKED_NO_LIVE_QUOTES','thresholds':asdict(cfg),'calendar':cal,'sources':manifest}
    (a.out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in summary.items() if k not in ['calendar','sources','thresholds']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
