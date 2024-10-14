from datetime import datetime
import backtrader as bt
from utils.basic import read_data, transfer_period
from utils.basic import read_shfe_data
import pandas as pd


# Create a subclass of Strategy to define the indicators and logic

class MyStrategy(bt.Strategy):
    # list of parameters which are configurable for the strategy
    params = dict(
        pfast=12,  # period for the fast moving average
        pslow=21  # period for the slow moving average
    )

    def __init__(self):
        self.order = None
        self.sma1 = bt.talib.SMA(self.data.close, timeperiod=self.p.pfast, plotname='TA_SMA1')
        self.sma2 = bt.talib.SMA(self.data.close, timeperiod=self.p.pslow, plotname='TA_SMA2')
        self.hammer = bt.talib.CDLHANGINGMAN(self.data.open, self.data.high, self.data.low,
                                             self.data.close)
        # self.sma1 = bt.ind.SMA(period=self.p.pfast)  # fast moving average
        # self.sma2 = bt.ind.SMA(period=self.p.pslow)  # slow moving average
        self.crossover = bt.ind.CrossOver(self.sma1, self.sma2)  # crossover signal

    def next(self):
        if self.datas[0].close[0] > self.sma2[0] and self.crossover > 0:  # if fast crosses slow to the upside
            self.order = self.order_target_size(target=1)  # enter long
        elif self.datas[0].close[0] < self.sma2[0] and self.crossover < 0:
            self.order = self.order_target_size(target=-1)


cerebro = bt.Cerebro()  # create a "Cerebro" engine instance

data = read_shfe_data("../data/MarketData_Year_2024")
data = data[data["Contract"] == "ag2407"]
data['Date'] = pd.to_datetime(data['Date'], format='%Y%m%d')
data['Open'] = data['Open'].fillna(data['Close'])
data['High'] = data['High'].fillna(data['Close'])
data['Low'] = data['Low'].fillna(data['Close'])
data.set_index('Date', inplace=True)

# dfdata = read_data('../data/SA/SA主力连续.csv')
# dfday = transfer_period(dfdata, "D")
# dfday['date'] = pd.to_datetime(dfday.index)

data = bt.feeds.PandasData(dataname=data)
cerebro.adddata(data)  # Add the data feed

cerebro.addstrategy(MyStrategy)  # Add the trading strategy
cerebro.broker.setcash(10000.0)

# Add a FixedSize sizer according to the stake
# cerebro.addsizer(bt.sizers.FixedSize, stake=10)

# Set the commission
# cerebro.broker.setcommission(commission=0.00025)
cerebro.broker.setcommission(commission=0.00025,  # 保证金比例
                             mult=10.0, leverage=10, automargin=True, commtype=bt.CommInfoBase.COMM_PERC)
cerebro.addsizer(bt.sizers.FixedSize, stake=1)
cerebro.run()  # run it all
portval = cerebro.broker.getvalue()
print(f"剩余资金：{portval}")
cerebro.plot(style='candlestick')  # and plot it with a single command
