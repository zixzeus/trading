from datetime import datetime
import backtrader as bt
from utils.basic import read_data,transfer_period
import pandas as pd
# Create a subclass of Strategy to define the indicators and logic

class MyStrategy(bt.Strategy):
    # list of parameters which are configurable for the strategy
    params = dict(
        pfast=5,  # period for the fast moving average
        pslow=21   # period for the slow moving average
    )

    def __init__(self):
        self.order = None
        self.sma1=bt.talib.SMA(self.data.close, timeperiod=self.p.pfast, plotname='TA_SMA1')
        self.sma2 = bt.talib.SMA(self.data.close, timeperiod=self.p.pslow, plotname='TA_SMA2')
        self.hammer = bt.talib.CDLHANGINGMAN(self.data.open, self.data.high, self.data.low,
                    self.data.close)
        # self.sma1 = bt.ind.SMA(period=self.p.pfast)  # fast moving average
        # self.sma2 = bt.ind.SMA(period=self.p.pslow)  # slow moving average
        self.crossover = bt.ind.CrossOver(self.sma1, self.sma2)  # crossover signal

    def next(self):
        if not self.position:  # not in the market
            if self.datas[0].close[0] > self.sma2[0]:  # if fast crosses slow to the upside
                self.order=self.buy(size=10)  # enter long
            elif self.datas[0].close[0] < self.sma2[0]:
                self.order=self.sell(size=10)
        else:
            if self.datas[0].close[0] < self.sma2[0]:  # in the market & cross to the downside
                self.order=self.close(size=10)  # close long position
            elif self.datas[0].close[0] > self.sma2[0]:
                self.order=self.close(size=10)

cerebro = bt.Cerebro()  # create a "Cerebro" engine instance

# Create a data feed
# data = bt.feeds.YahooFinanceData(dataname='MSFT',
#                                  fromdate=datetime(2011, 1, 1),
#                                  todate=datetime(2012, 12, 31))
dfdata = read_data('../data/SA/SA主力连续.csv')
dfday = transfer_period(dfdata, "D")
dfday['date'] = pd.to_datetime(dfday.index)
dfday['date'] = dfday['date'].apply(lambda x: x.strftime('%Y-%m-%d'))

data = bt.feeds.PandasData(dataname=dfday)
cerebro.adddata(data)  # Add the data feed

cerebro.addstrategy(MyStrategy)  # Add the trading strategy
cerebro.broker.setcash(100000.0)

# Add a FixedSize sizer according to the stake
# cerebro.addsizer(bt.sizers.FixedSize, stake=10)

# Set the commission
cerebro.broker.setcommission(commission=0.00025)
cerebro.run()  # run it all
portval = cerebro.broker.getvalue()
print(f"剩余资金：{portval}")
cerebro.plot()  # and plot it with a single command