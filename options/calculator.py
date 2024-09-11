from scipy.stats import norm
from math import log, exp, sqrt
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import QuantLib as ql


class HistoryData:
    def __init__(self, filepath):
        self.data = pd.read_csv(filepath, encoding='utf-8')
        self.data['Date'] = pd.to_datetime(self.data['Date'])
        self.data = self.data.dropna(axis=0)
        self._date_range = None

    @property
    def date_range(self):
        return self._date_range

    @date_range.setter
    def date_range(self, params):
        self._date_range = pd.date_range(params[0], params[1])

    def history_vol(self):
        if self.date_range is not None:
            self.data = self.data[self.data['Date'].isin(self.date_range)]
        self.data["return"] = np.log(self.data["Price"] / self.data["Price"].shift(1))
        self.data["vol"] = self.data["return"].rolling(21).std() * sqrt(252)

    def show(self, type):
        if type == "VOL":
            plt.plot(self.data["Date"], self.data["vol"])
            plt.title("silver's history vol")
            plt.xlabel("Date")
            plt.ylabel(f"History {type}")
        elif type == "MONTH_VOL":
            monthly_vol = self.monthly_vol()
            monthly_vol.plot(kind="line")
            plt.xlabel("MONTH")
            plt.ylabel(f"History {type}")
        elif type == "VOL_DIS":
            self.vol_distribution()
            plt.xlabel("VOL")
            plt.ylabel(f"Frequency")
        plt.show()

    def monthly_vol(self):
        # 以月份为单位对价格进行分组并计算平均值
        if "vol" not in self.data.columns:
            self.history_vol()
        monthly_prices = self.data.groupby(self.data['Date'].dt.strftime('%m'))['vol'].mean()
        return monthly_prices

    def vol_distribution(self):
        if "vol" not in self.data.columns:
            self.history_vol()
        plt.hist(self.data['vol'], bins=50, density=True, alpha=0.6, color='b',
                 label='vol Change Histogram')


class ImpliedVolatility(object):
    risk_free_rate = 0.015
    dividend_rate = 0.0

    def __init__(self, option_pirce, current_price, strike_price, expiration_date, option_type):
        self.option_pirce = option_pirce
        self.current_price = current_price
        self.strike_price = strike_price
        self.expiration_date = expiration_date
        self.option_type = option_type

    def implied_vol(self):
        calendar = ql.China()
        day_count = ql.Actual365Fixed()
        today = ql.Date.todaysDate()
        ql.Settings.instance().evaluationDate = today
        payoff = ql.PlainVanillaPayoff(self.option_type, self.strike_price)
        exercise = ql.AmericanExercise(today, self.expiration_date)
        american_option = ql.VanillaOption(payoff, exercise)
        spot_handle = ql.QuoteHandle(ql.SimpleQuote(self.current_price))
        rate_handle = ql.YieldTermStructureHandle(ql.FlatForward(today, self.risk_free_rate, day_count))
        dividend_handle = ql.YieldTermStructureHandle(ql.FlatForward(today, self.dividend_rate, day_count))
        initial_volatility = 0.2
        volatility_handle = ql.BlackVolTermStructureHandle(
            ql.BlackConstantVol(today, calendar, initial_volatility, day_count))

        # 使用 Black-Scholes-Merton 模型进行期权定价
        bsm_process = ql.BlackScholesMertonProcess(spot_handle, dividend_handle, rate_handle, volatility_handle)

        # 设置定价引擎
        # european_option.setPricingEngine(ql.AnalyticEuropeanEngine(bsm_process))
        binomial_steps = 1000
        american_option.setPricingEngine(ql.BinomialVanillaEngine(bsm_process, "crr", binomial_steps))
        # 计算隐含波动率
        # implied_vol = european_option.impliedVolatility(market_price, bsm_process)
        implied_vol = american_option.impliedVolatility(self.current_price, bsm_process)
        return implied_vol

class Calculator:
    def __init__(self, current_price, target_price, left_time, volatility, option_type):
        self.strike_price = target_price
        self.future_price = current_price
        self.option_type = option_type
        self.option_price = None
        self.volatility = volatility
        self.maturity_time = left_time
        self.prob = 0
        self.interest_rate = 0.015

    def history_vol(self):
        pass

    def predicate_time_span(self):
        pass

    def predicate_price_span(self, prob):
        T = self.maturity_time / 365
        r = self.interest_rate
        d = self.volatility
        mu = (r - d * d * 0.5) * T
        std = sqrt(d * d * T)
        p_below = (1 - prob) / 2
        price_below = norm.ppf(p_below, loc=mu, scale=std)
        p_above = (1 + prob) / 2
        price_above = norm.ppf(p_above, loc=mu, scale=std)
        S = self.future_price
        return [S * exp(price_below), S * exp(price_above)]

    def probability(self):
        T = self.maturity_time / 365
        r = self.interest_rate
        d = self.volatility
        mu = (r - d * d * 0.5) * T
        std = sqrt(d * d * T)
        v = log(self.strike_price / self.future_price)

        p_below = norm.cdf(v, loc=mu, scale=std)
        p_above = 1 - p_below

        if self.option_type == ql.Option.Put:
            return p_below
        elif self.option_type == ql.Option.Call:
            return p_above


# 输入期权相关信息


if __name__ == '__main__':
    current_price = 3040
    target_price = 3350
    left_time = 98
    volatility = 0.5
    option_type = ql.Option.Call

    ca = Calculator(current_price, target_price, left_time, volatility, option_type)
    print(ca.probability())

    print(ca.predicate_price_span(0.8))

    filepath = "../data/silver.csv"
    silver_his = HistoryData(filepath)
    silver_his.date_range = ("2012-01-1", "2023-12-31")
    silver_his.history_vol()
    silver_his.show("VOL")
    silver_his.show("MONTH_VOL")
    silver_his.show("VOL_DIS")
