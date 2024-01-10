from scipy.stats import norm
from math import log,exp,sqrt

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



if __name__ == '__main__':
    current_price=1867
    target_price=2000
    left_time =92
    volatility = 0.3662
    direction = "CALL"

    ca = Calculator(current_price,target_price,left_time,volatility,direction)
    print(ca.probability())

    print(ca.predicate_price_span(0.99))




