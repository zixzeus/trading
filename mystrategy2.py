from datetime import datetime
import backtrader as bt
from basic import read_data,transfer_period
import pandas as pd
# Create a subclass of Strategy to define the indicators and logic

class MyStrategy(bt.Strategy):
    # list of parameters which are configurable for the strategy
    params = dict(
        pfast=5,  # period for the fast moving average
        pslow=21,   # period for the slow moving average
        holdday=4
    )

    def __init__(self):
        self.order = None
        self.sma1 = bt.talib.SMA(self.data.close, timeperiod=self.params.pfast, plotname='TA_SMA1')
        self.sma2 = bt.talib.SMA(self.data.close, timeperiod=self.params.pslow, plotname='TA_SMA2')
        self.hammer = bt.talib.CDLENGULFING(self.data.open, self.data.high, self.data.low,
                    self.data.close)
        self.crossover = bt.ind.CrossOver(self.sma1, self.sma2)  # crossover signal
        self.open_interest = (self.data.openinterest(0)/self.data.openinterest(-1)-1)



    def next(self):
        # if not self.position:  # not in the market
        if (self.hammer[0] == -100 or self.hammer[0] == 100)and self.open_interest[0]>0.06  :  # if fast crosses slow to the upside
            self.sell()  # enter long
            print("仓差:",self.open_interest[0])

        if self.hammer[-self.params.holdday] == -100 or self.hammer[-self.params.holdday] == 100:  # in the market & cross to the downside
            self.close()  # close long position


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
cerebro.broker.setcommission(commission=0.00025,leverage=5,mult=20)
# cerebro.addsizer(bt.sizers.PercentSizerInt, percents=60)
# Add a FixedSize sizer according to the stake
cerebro.addsizer(bt.sizers.FixedSize, stake=1)


# Set the commission



cerebro.addobserver(bt.observers.Broker)
cerebro.addobserver(bt.observers.Trades)
cerebro.addobserver(bt.observers.DrawDown)

# Set leverage
# cerebro.broker.setcommission()
# 添加分析指标
# 收益率
cerebro.addanalyzer(bt.analyzers.Returns, _name='_Returns')
# 收益期间
cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='_TimeReturn')
# 计算最大回撤相关指标
cerebro.addanalyzer(bt.analyzers.DrawDown, _name='_DrawDown')
# 回撤期间
cerebro.addanalyzer(bt.analyzers.TimeDrawDown, _name='_TimeDrawDown')
# 计算年化夏普比率
cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='_SharpeRatio', timeframe=bt.TimeFrame.Days, annualize=True,
                    riskfreerate=0)  # 计算夏普比率
# 交易统计信息，如获胜、失败次数
cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='_TradeAnalyzer')
result=cerebro.run()  # run it all

print("--------------- 收益期间 -----------------")
print(result[0].analyzers._TimeReturn.get_analysis())
print("--------------- 最大回撤相关指标 -----------------")
print(result[0].analyzers._DrawDown.get_analysis())
print("--------------- 回撤期间 -----------------")
print(result[0].analyzers._TimeDrawDown.get_analysis())
print(f"最终资金: {cerebro.broker.getvalue():,.2f} 元")
print("收益率：", result[0].analyzers._Returns.get_analysis()['rtot'])
print("夏普比率：", result[0].analyzers._SharpeRatio.get_analysis()['sharperatio'])
print("赢",result[0].analyzers._TradeAnalyzer.get_analysis()['won'])
print("亏",result[0].analyzers._TradeAnalyzer.get_analysis()['lost'])
print(result[0].analyzers._TradeAnalyzer.get_analysis()['streak'])
win_time = result[0].analyzers._TradeAnalyzer.get_analysis()['won']['total']
all_trades_time = result[0].analyzers._TradeAnalyzer.get_analysis()['total']['total']
print("指标胜率",win_time/all_trades_time)
# 绘制图表

portval = cerebro.broker.getvalue()
print(f"剩余资金：{portval}")
cerebro.plot(tight=True,dpi=600)  # and plot it with a single command