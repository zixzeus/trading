import copy
import json
from pathlib import Path
import unittest
from datetime import datetime
from options.expiry_scanner.scanner import *
HERE=Path(__file__).resolve().parents[1]
class Tests(unittest.TestCase):
    def setUp(self):
        self.c=calendar_load(HERE/'calendar_20261019_20261130.json')
        self.r=json.loads((HERE/'example_live_SYNTHETIC.json').read_text())
        self.now=aware('2026-10-20T09:10:00+08:00')
    def run_r(self,**changes):
        r=copy.deepcopy(self.r);r.update(changes);return evaluate_live(r,self.now,self.c)
    def test_synthetic_trigger(self):
        x=self.run_r();self.assertEqual(x['status'],'RESEARCH_TRIGGER_ONLY');self.assertIsNone(x['order']);self.assertEqual(x['max_premium_loss_plus_fees'],5020)
    def test_time(self):
        self.assertEqual(classify('2026-10-26',self.now,self.c),('near_1_5_trading_days',4))
        self.assertEqual(classify('2026-10-19',self.now,self.c),('expired',-1))
        self.assertEqual(classify('2026-10-20',self.now,self.c),('0DTE',0))
        self.assertEqual(classify('2026-10-20',aware('2026-10-20T15:00:00+08:00'),self.c)[0],'expired_today_after_trading_cutoff')
        self.assertEqual(classify(None,self.now,self.c)[0],'unknown_expiry')
        self.assertEqual(classify('2027-01-01',self.now,self.c)[0],'calendar_out_of_range')
    def test_config_invalid(self):
        for x in [float('nan'),-1,0,1,2]:
            with self.assertRaises(ValueError):Config(max_loss_fraction=x)
    def test_no_naive_time(self):
        with self.assertRaises(ValueError):aware('2026-10-20T09:00:00')
    def test_missing_every_field(self):
        for k in self.r:
            r=copy.deepcopy(self.r);r.pop(k)
            with self.subTest(k=k):self.assertEqual(evaluate_live(r,self.now,self.c)['status'],'BLOCKED')
    def test_invalid_boundaries(self):
        mutations=[dict(underlying=123),dict(session_start='2026-10-20T09:00:01+08:00'),dict(range_end='2026-10-20T09:04:00+08:00'),dict(previous_bar_end='2026-10-20T09:05:00+08:00',bar_seconds=300),dict(last_trade_at='2026-10-26T16:00:00+08:00'),dict(broker_exercise_cutoff='2026-10-26T16:00:00+08:00'),dict(trading_day='2026-11-20'),dict(exchange='GFEX'),dict(previous_bar_end='2026-10-20T09:08:00+08:00'),dict(session_start='2026-10-20T12:00:00+08:00',session_end='2026-10-20T13:15:00+08:00'),dict(bid=0),dict(bid=1001),dict(bid=float('nan')),dict(ask=float('inf')),dict(bid=991),dict(ask_size=4),dict(volume=99),dict(open_interest=99),dict(ask=1100),dict(quantity=1.5),dict(multiplier=0),dict(fees_roundtrip=-1),dict(equity=1000),dict(risk_budget=5019),dict(daily_loss=26000),dict(open_premium_risk=26000),dict(quote_timestamp='2026-10-20T09:09:56+08:00'),dict(future_timestamp='2026-10-20T09:09:58+08:00'),dict(quote_timestamp='2026-10-20T09:10:01+08:00'),dict(bar_end='2026-10-20T09:10:01+08:00'),dict(bar_end='2026-10-20T09:09:55+08:00'),dict(range_end='2026-10-20T09:10:00+08:00'),dict(session_end='2026-10-20T15:00:00+08:00'),dict(flatten_by='2026-10-20T10:00:00+08:00'),dict(underlying='cu2612'),dict(future_contract='cu2612'),dict(style='Unknown'),dict(session_verified=False),dict(broker_rules_verified=False),dict(exercise_risk_acknowledged=False),dict(options_permission_verified=False),dict(previous_close=110020),dict(relative_volume=1.49),dict(max_exit_slippage_ticks=2),dict(expiry='2026-10-19'),dict(trading_day='2026-10-18'),dict(future_upper_limit=110080)]
        for m in mutations:
            with self.subTest(m=m):self.assertEqual(self.run_r(**m)['status'],'BLOCKED')
    def test_put(self):
        x=self.run_r(contract='cu2611P110000',right='P',future_bid=109740,future_ask=109750,confirmed_close=109760,previous_close=109770)
        self.assertEqual(x['status'],'RESEARCH_TRIGGER_ONLY')
    def test_exact_risk_boundary(self):self.assertEqual(self.run_r(risk_budget=5020)['status'],'RESEARCH_TRIGGER_ONLY')
    def test_inclusive_age(self):
        x=self.run_r(quote_timestamp='2026-10-20T09:09:57+08:00',future_timestamp='2026-10-20T09:09:57+08:00');self.assertEqual(x['status'],'RESEARCH_TRIGGER_ONLY')
    def test_breakout_exact_is_not_break(self):self.assertEqual(self.run_r(previous_close=110020)['status'],'BLOCKED')
    def test_eod_exclusions(self):
        raw=pd.DataFrame([dict(exchange='X',contract='cu2611C110000',strike=110000,series='cu2611',volume=1000,open_interest=1000,close=100,trade_date='20261019')])
        m=pd.DataFrame([dict(exchange='X',contract='cu2611C110000',expiry='2026-10-19',underlying_verified='cu2611',future=110000,future_date='20261019',future_source='official',metadata_source='official',tick_size=2,multiplier=5,style='American')])
        _,w=screen(raw,m,self.now,self.c);self.assertEqual(len(w),0)
        m['expiry']='2026-10-26';_,w=screen(raw,m,self.now,self.c);self.assertEqual(len(w),1)
        m['underlying_verified']='cu2612';_,w=screen(raw,m,self.now,self.c);self.assertEqual(len(w),0)
        m['underlying_verified']='cu2611'
        m['future_date']='20261018';_,w=screen(raw,m,self.now,self.c);self.assertEqual(len(w),0)
if __name__=='__main__':unittest.main()
