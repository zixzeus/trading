from scipy.stats import norm
from math import log, exp, sqrt
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import QuantLib as ql
import timeit


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

    def history_vol(self, window=21):
        if self.date_range is not None:
            self.data = self.data[self.data['Date'].isin(self.date_range)]
        self.data["return"] = np.log(self.data["Price"] / self.data["Price"].shift(1))
        self.data["vol"] = self.data["return"].rolling(window=window).std() * sqrt(252)

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


class ImVolCalculator:
    risk_free_rate = 0.015
    dividend_rate = 0.0

    def __init__(self):
        self._option_price = None
        self._current_price = None
        self._strike_price = None
        self._expiration_date = None
        self._evaluation_date = None
        self._option_type = None
        self.random_process = None
        self.option_engine = None
        self.implied_volatility = 0
        self.greek = {}

    def check_initialized(self):
        for name, value in vars(self).items():
            if value is None:
                raise AttributeError(f"{name} is not initialized")

    @property
    def option_price(self):
        return self._option_price

    @option_price.setter
    def option_price(self, params):
        self._option_price = params

    @property
    def current_price(self):
        return self._current_price

    @current_price.setter
    def current_price(self, params):
        self._current_price = params

    @property
    def strike_price(self):
        return self._strike_price

    @strike_price.setter
    def strike_price(self, params):
        self._strike_price = params

    @property
    def expiration_date(self):
        return self._expiration_date

    @expiration_date.setter
    def expiration_date(self, params):
        self._expiration_date = params

    @property
    def evaluation_date(self):
        return self._evaluation_date

    @evaluation_date.setter
    def evaluation_date(self, params):
        self._evaluation_date = params

    @property
    def option_type(self):
        return self._option_type

    @option_type.setter
    def option_type(self, params):
        self._option_type = params

    def load_bs_model(self):

        # 设置 QuantLib 的日期结构
        calendar = ql.China()
        day_count = ql.Actual365Fixed()

        today = self.evaluation_date
        ql.Settings.instance().evaluationDate = today
        # 创建期权标的物
        payoff = ql.PlainVanillaPayoff(self.option_type, self.strike_price)
        # 设置市场数据
        spot_handle = ql.QuoteHandle(ql.SimpleQuote(self.current_price))
        rate_handle = ql.YieldTermStructureHandle(ql.FlatForward(today, self.risk_free_rate, day_count))
        dividend_handle = ql.YieldTermStructureHandle(ql.FlatForward(today, self.dividend_rate, day_count))
        # 初始波动率猜测
        initial_volatility = 0.2
        volatility_handle = ql.BlackVolTermStructureHandle(
            ql.BlackConstantVol(today, calendar, initial_volatility, day_count))

        # 使用 Black-Scholes-Merton 模型进行期权定价
        self.random_process = ql.BlackScholesMertonProcess(spot_handle, dividend_handle, rate_handle, volatility_handle)

        exercise = ql.EuropeanExercise(self.expiration_date)
        self.option_engine = ql.VanillaOption(payoff, exercise)

        # 设置定价引擎
        self.option_engine.setPricingEngine(ql.AnalyticEuropeanEngine(self.random_process))
        # 计算隐含波动率
        # self.implied_volatility = europe_option.impliedVolatility(self.option_price, bsm_process)

    def get_implied_volatility(self):
        self.implied_volatility = self.option_engine.impliedVolatility(self.option_price, self.random_process)

    def get_greek(self):
        self.greek["Delta"] = self.option_engine.delta()
        self.greek["Gamma"] = self.option_engine.gamma()
        self.greek["Theta"] = self.option_engine.thetaPerDay()
        self.greek["Vega"] = self.option_engine.vega()


class VolCalculator:
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


class OptionCalculator:
    risk_free_rate = 0.015
    dividend_rate = 0.0

    def __init__(self):
        self._option_price = None
        self._current_price = None
        self._strike_price = None
        self._expiration_date = None
        self._evaluation_date = None
        self._option_type = None
        self.random_process = None
        self.option_engine = None
        self._implied_volatility = 0
        self.greek = {}

    @property
    def option_price(self):
        return self._option_price

    @option_price.setter
    def option_price(self, params):
        self._option_price = params

    @property
    def implied_volatility(self):
        return self._implied_volatility

    @implied_volatility.setter
    def implied_volatility(self, volatility):
        self._implied_volatility = volatility

    @property
    def current_price(self):
        return self._current_price

    @current_price.setter
    def current_price(self, params):
        self._current_price = params

    @property
    def strike_price(self):
        return self._strike_price

    @strike_price.setter
    def strike_price(self, params):
        self._strike_price = params

    @property
    def expiration_date(self):
        return self._expiration_date

    @expiration_date.setter
    def expiration_date(self, params):
        self._expiration_date = params

    @property
    def evaluation_date(self):
        return self._evaluation_date

    @evaluation_date.setter
    def evaluation_date(self, params):
        self._evaluation_date = params

    @property
    def option_type(self):
        return self._option_type

    @option_type.setter
    def option_type(self, params):
        self._option_type = params

    def load_bs_model(self):
        calendar = ql.China()
        day_count = ql.Actual365Fixed()
        calculation_date = calendar.adjust(self.evaluation_date)
        ql.Settings.instance().evaluationDate = calculation_date
        payoff = ql.PlainVanillaPayoff(self.option_type, self.strike_price)
        exercise = ql.EuropeanExercise(self.expiration_date)
        self.option_engine = ql.VanillaOption(payoff, exercise)

        spot_handle = ql.QuoteHandle(ql.SimpleQuote(self.current_price))
        flat_ts = ql.YieldTermStructureHandle(ql.FlatForward(calculation_date, self.risk_free_rate, day_count))
        flat_vol_ts = ql.BlackVolTermStructureHandle(
            ql.BlackConstantVol(calculation_date, calendar, self.implied_volatility, day_count))
        self.random_process = ql.BlackScholesProcess(spot_handle, flat_ts, flat_vol_ts)

        self.option_engine.setPricingEngine(ql.AnalyticEuropeanEngine(self.random_process))

    def get_option_price(self):
        self.option_price = self.option_engine.NPV()


# 输入期权相关信息


if __name__ == '__main__':
    option_price = 25.5
    current_price = 3150
    strike_price = 3250
    expiration_date = ql.Date(25, 11, 2024)
    evaluate_date = ql.Date(16, 11, 2024)
    option_type = ql.Option.Put
    #
    # ca = VolCalculator(current_price, strike_price, left_time, volatility, option_type)
    # print(ca.probability())
    #
    # print(ca.predicate_price_span(0.8))
    #
    #
    # # start_time = time.time()
    # def a():

    # Iv = ImVolCalculator()
    # # Iv.check_initialized()
    # Iv.option_price = option_price
    # Iv.strike_price = strike_price
    # Iv.expiration_date = expiration_date
    # Iv.current_price = current_price
    # Iv.evaluation_date = evaluate_date
    # Iv.option_type = option_type
    # Iv.load_bs_model()
    # Iv.check_initialized()
    # Iv.get_greek()
    # Iv.get_implied_volatility()
    # print(Iv.implied_volatility)
    # print(Iv.greek)

    OptionC = OptionCalculator()
    # OptionC.option_price = option_price
    OptionC.implied_volatility = 0.15311265595727777
    OptionC.strike_price = strike_price
    OptionC.expiration_date = expiration_date
    OptionC.current_price = current_price
    OptionC.evaluation_date = evaluate_date
    OptionC.option_type = option_type
    OptionC.load_bs_model()
    OptionC.get_option_price()
    print(OptionC.option_price)
    #
    #     # for option in range(190, 200):
    #     #     for strike in range(24000, 25000):
    #     #         Iv.option_price = option
    #     #         Iv.strike_price = strike
    #     Iv.load_bs_model()
    #     Iv.check_initialized()
    #     Iv.get_greek()
    #     print(Iv.greek)
    #
    # execution_time = timeit.timeit("a()", globals=locals(), number=1)
    # print("Execution Time: ", execution_time)

    # filepath = "../data/silver.csv"
    # silver_his = HistoryData(filepath)
    # silver_his.date_range = ("2012-01-1", "2023-12-31")
    # silver_his.history_vol()
    # silver_his.show("VOL")
    # silver_his.show("MONTH_VOL")
    # silver_his.show("VOL_DIS")
