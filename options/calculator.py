from scipy.stats import norm
from math import log,exp,sqrt
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import QuantLib as ql
class HistoryData:
    def __init__(self,filepath):
        self.data = pd.read_csv(filepath,encoding = 'utf-8')
        self.data['Date'] = pd.to_datetime(self.data['Date'])
        self.data = self.data.dropna(axis=0)
        self._date_range = None

    @property
    def date_range(self):
        return self._date_range

    @date_range.setter
    def date_range(self,params):
        self._date_range = pd.date_range(params[0],params[1])

    def history_vol(self):
        if self.date_range is not None:
            self.data = self.data[self.data['Date'].isin(self.date_range)]
        self.data["return"] = np.log(self.data["Price"]/self.data["Price"].shift(1))
        self.data["vol"] = self.data["return"].rolling(21).std()*sqrt(252)

    def show(self,type):
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

class Calculator:
    def __init__(self,current_price,target_price,left_time,volatility,direction):
        self.strike_price = target_price
        self.future_price = current_price
        self.direction = direction
        self.option_price = None
        self.volatility = volatility
        self.maturity_time = left_time
        self.prob = 0
        self.interest_rate = 0.015

    def history_vol(self):
        pass

    def predicate_time_span(self):
        pass

    def predicate_price_span(self,prob):
        T = self.maturity_time/365
        r = self.interest_rate
        d= self.volatility
        mu = (r - d*d*0.5)*T
        std = sqrt(d*d*T)
        p_below=(1-prob)/2
        price_below = norm.ppf(p_below,loc=mu,scale=std)
        p_above=(1+prob)/2
        price_above = norm.ppf(p_above,loc=mu,scale=std)
        S=self.future_price
        return [S*exp(price_below),S*exp(price_above)]
    def probability(self):
        T = self.maturity_time/365
        r = self.interest_rate
        d= self.volatility
        mu = (r - d*d*0.5)*T
        std = sqrt(d*d*T)
        v = log(self.strike_price/self.future_price)

        p_below = norm.cdf(v,loc=mu,scale=std)
        p_above = 1- p_below

        if (self.direction == "PUT"):
            return p_below
        elif self.direction == "CALL":
            return p_above


# 输入期权相关信息


if __name__ == '__main__':
    current_price=4459
    target_price=4000
    left_time =300
    volatility = 0.1763
    direction = "PUT"

    ca = Calculator(current_price,target_price,left_time,volatility,direction)
    print(ca.probability())

    print(ca.predicate_price_span(0.99))


    filepath = "../data/silver.csv"
    silver_his = HistoryData(filepath)
    silver_his.date_range =("2012-01-1","2023-12-31")
    silver_his.history_vol()
    silver_his.show("VOL")
    silver_his.show("MONTH_VOL")
    silver_his.show("VOL_DIS")

