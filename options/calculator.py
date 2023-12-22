class Calculator:
    def __init__(self,current_price,target_price,left_time,volatility):
        self.strike_price = target_price
        self.future_price = current_price
        self.option_price = None
        self.volatility = volatility
        self.maturity_time = left_time
        self.prob = 0

    def history_vol(self):
        pass

    def predicate_time_span(self):
        pass

    def predicate_price_span(self):
        pass




