from datetime import datetime
import backtrader as bt
from utils.basic import read_data, transfer_period
import pandas as pd
from utils.basic import read_shfe_data


# Create a subclass of Strategy to define the indicators and logic

class SmaCross(bt.Strategy):
    # list of parameters which are configurable for the strategy
    params = dict(
        pfast=10,  # period for the fast moving average
        pslow=30  # period for the slow moving average
    )

    def __init__(self):
        sma1 = bt.ind.SMA(period=self.p.pfast)  # fast moving average
        sma2 = bt.ind.SMA(period=self.p.pslow)  # slow moving average
        self.crossover = bt.ind.CrossOver(sma1, sma2)  # crossover signal

    def next(self):
        if not self.position:  # not in the market
            if self.crossover > 0:  # if fast crosses slow to the upside
                self.buy()  # enter long

        elif self.crossover < 0:  # in the market & cross to the downside
            self.close()  # close long position


cerebro = bt.Cerebro()  # create a "Cerebro" engine instance

# Create a data feed
# data = bt.feeds.YahooFinanceData(dataname='MSFT',
#                                  fromdate=datetime(2011, 1, 1),
#                                  todate=datetime(2012, 12, 31))
# dfdata = read_data('../data/SA/SA主力连续.csv')
# dfday = transfer_period(dfdata, "D")
# dfday['date'] = pd.to_datetime(dfday.index)
# dfday['date'] = dfday['date'].apply(lambda x: x.strftime('%Y-%m-%d'))
# data = bt.feeds.PandasData(dataname=dfday)

data = read_shfe_data("../data/MarketData_Year_2024")
data = data[data["Contract"] == "ag2405"]
# data['Contract'] = data['Contract'].apply(lambda x: f"{x}.SHFE")
data['Date'] = pd.to_datetime(data['Date'], format='%Y%m%d')
data.set_index('Date', inplace=True)
data = bt.feeds.PandasData(dataname=data)


cerebro.adddata(data)  # Add the data feed
cerebro.addstrategy(SmaCross)

cerebro.broker.setcash(100000.0)
cerebro.broker.setcommission(commission=0.00025)
cerebro.addsizer(bt.sizers.FixedSize, stake=10)
# Add the trading strategy
cerebro.run()  # run it all
portval = cerebro.broker.getvalue()
print(f"剩余资金：{portval}")
cerebro.plot()  # and plot it with a single command
