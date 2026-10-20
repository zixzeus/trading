import unittest
import numpy as np
import pandas as pd
from options.value_scanner_v2.scanner import (Config, american76,black76,implied_vol,
    loo_smile,parse_contract,shape_flags,apply_metadata,scan,model_price)

class Models(unittest.TestCase):
    def test_contracts(self):
        self.assertEqual(parse_contract('AP612C5700'),('AP612','C',5700.))
        self.assertEqual(parse_contract('ps2612-C-31500'),('ps2612','C',31500.))
        self.assertIsNone(parse_contract('合计'))
        self.assertEqual(parse_contract('SR701MSC4700'),('SR701MS','C',4700.))
    def test_european_roundtrip(self):
        for right in ['C','P']:
            p=black76(100,110,.25,.02,.3,right)
            self.assertAlmostEqual(implied_vol(p,100,110,.25,.02,right),.3,places=6)
    def test_american_roundtrip(self):
        for right in ['C','P']:
            p=american76(100,110,.25,.02,.3,right)
            self.assertAlmostEqual(implied_vol(p,100,110,.25,.02,right,'American'),.3,places=6)
    def test_american_bounds(self):
        for right in ['C','P']:
            for k in [80,100,120]:
                a=american76(100,k,.5,.05,.3,right,800)
                e=black76(100,k,.5,.05,.3,right)
                intrinsic=max((1 if right=='C' else -1)*(100-k),0)
                self.assertGreaterEqual(a+0.008,e)
                self.assertGreaterEqual(a,intrinsic)
    def test_zero_rate(self):
        for right in ['C','P']:
            self.assertAlmostEqual(american76(100,110,.4,0,.25,right,1200),black76(100,110,.4,0,.25,right),delta=.005)
    def test_strike_monotonicity(self):
        for model in [american76,black76]:
            self.assertGreater(model(100,90,.4,.02,.3,'C'),model(100,110,.4,.02,.3,'C'))
            self.assertLess(model(100,90,.4,.02,.3,'P'),model(100,110,.4,.02,.3,'P'))
    def test_invalid_price(self):
        self.assertTrue(np.isnan(implied_vol(-1,100,100,.5,.02,'C')))
        self.assertTrue(np.isnan(implied_vol(200,100,100,.5,.02,'C')))
    def test_unknown_style(self):
        with self.assertRaises(ValueError):model_price(100,100,.5,.02,.3,'C','unknown')
    def test_unknown_right(self):
        with self.assertRaises(ValueError):model_price(100,100,.5,.02,.3,'X','American')
    def test_zero_tenor(self):
        with self.assertRaises(ValueError):american76(100,100,0,.02,.3,'C')
    def test_parity(self):
        self.assertAlmostEqual(black76(100,110,.25,.02,.3,'C')-black76(100,110,.25,.02,.3,'P'),-10*np.exp(-.02*.25))

class Fitting(unittest.TestCase):
    def test_no_extrapolation(self):
        self.assertIsNone(loo_smile(np.arange(100,120),np.repeat(.3,20),90))
    def test_minimum_peers(self):
        self.assertIsNone(loo_smile([90,95,105,110],[.3]*4,100))
    def test_target_excluded(self):
        k=np.arange(90,111,2);v=np.repeat(.3,len(k));idx=np.where(k==100)[0][0]
        v[idx]=.01;a=loo_smile(k,v,100);v[idx]=2;b=loo_smile(k,v,100)
        self.assertEqual(a,b);self.assertAlmostEqual(a[0],.3)
    def test_robust_outlier(self):
        k=np.arange(88,113,2);v=.3+.1*np.log(k/100)**2;v[0]=1.5
        fit=loo_smile(k,v,100)
        self.assertIsNotNone(fit);self.assertAlmostEqual(fit[0],.3,delta=.01)
    def test_shape_all_legs_flagged(self):
        d=pd.DataFrame(dict(exchange=['X']*3,series=['x1']*3,right=['C']*3,strike=[90,100,110],settlement=[20,19,5],tick_size=[.1]*3))
        f=shape_flags(d)
        self.assertTrue(all('settlement_convexity_violation' in x for x in f.values()))

class DataGates(unittest.TestCase):
    def base(self):
        return pd.DataFrame(dict(exchange=['X']*3,contract=['x2612C90','x2612C100','x2612P90'],series=['x2612']*3,
            right=['C','C','P'],strike=[90,100,90],underlying=[None]*3,published_iv=[.3]*3,
            iv_origin=['official_published_definition_unverified']*3,volume=[100]*3,open_interest=[100]*3,
            close=[20,10,20],settlement=[20,10,20]))
    def test_no_metadata_no_otm(self):
        d=apply_metadata(self.base(),None,'20261019')
        self.assertTrue(d.otm_status.eq('unverified').all())
        out=scan(d);self.assertFalse(out.trade_signal.any());self.assertFalse(out.relative_value_candidate.any())
    def test_otm_not_delta(self):
        f=pd.DataFrame(dict(contract_id=['x2612'],settle=[100],trade_date=['20261019'],source=['official']))
        d=apply_metadata(self.base(),None,'20261019',f)
        self.assertEqual(d.otm_status.tolist(),['not_otm','not_otm','otm'])
        self.assertFalse(d.metadata_valid.any())
    def test_stale_future(self):
        f=pd.DataFrame(dict(contract_id=['x2612'],settle=[100],trade_date=['20261018'],source=['official']))
        d=apply_metadata(self.base(),None,'20261019',f)
        self.assertFalse(d.future_valid.any())
    def test_expired_metadata(self):
        m=pd.DataFrame([dict(exchange='X',contract='x2612C90',underlying_verified='x2612',future=100,
            future_date='20261019',future_source='official',expiry='2026-10-18',style='American',rate=.02,metadata_source='official')])
        d=apply_metadata(self.base(),m,'20261019');self.assertFalse(d.metadata_valid.any())
    def test_wrong_underlying(self):
        b=self.base();b['underlying']='wrong'
        f=pd.DataFrame(dict(contract_id=['x2612'],settle=[100],trade_date=['20261019'],source=['official']))
        self.assertFalse(apply_metadata(b,None,'20261019',f).future_valid.any())
    def test_theoretical_candidate_never_trade_signal(self):
        k=np.arange(50.,181.,10);t=90/365
        b=pd.DataFrame(dict(exchange='X',contract=['x2701C'+str(int(x)) for x in k],series='x2701',right='C',strike=k,
            underlying='x2701',published_iv=np.nan,iv_origin='missing',volume=100,open_interest=100,
            close=[black76(100,x,t,.02,.275 if x==110 else .3,'C') for x in k]))
        b['settlement']=b.close
        m=pd.DataFrame(dict(exchange='X',contract=b.contract,underlying_verified='x2701',future=100,future_date='20261019',
            future_source='official',expiry='2027-01-17',style='European',rate=.02,metadata_source='official',tick_size=.001))
        d=scan(apply_metadata(b,m,'20261019'))
        self.assertTrue(d.loc[d.strike.eq(110),'relative_value_candidate'].iloc[0])
        self.assertFalse(d.trade_signal.any())
    def test_duplicate_metadata(self):
        m=pd.DataFrame([dict(exchange='X',contract='x2612C90',underlying_verified='x2612',future=100,
            future_date='20261019',future_source='official',expiry='2026-12-10',style='American',rate=.02,metadata_source='official')]*2)
        with self.assertRaises(ValueError):apply_metadata(self.base(),m,'20261019')

if __name__=='__main__':unittest.main()
