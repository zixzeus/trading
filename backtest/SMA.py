import backtrader as bt
import pandas as pd
# import quantstats
from custompandasdata import CustomPandasData
from utils.basic import read_data, transfer_period, read_shfe_data


# Create a subclass of Strategy to define the indicators and logic

class SmaCross(bt.Strategy):
    # list of parameters which are configurable for the strategy
    params = dict(
        pfast=5,  # period for the fast moving average
        pslow=10,  # period for the slow moving average
        mult=10,
    )

    def __init__(self):
        sma1 = bt.ind.SMA(period=self.p.pfast)  # fast moving average
        sma2 = bt.ind.SMA(period=self.p.pslow)  # slow moving average
        self.crossover = bt.ind.CrossOver(sma1, sma2)  # crossover signal
        # daily_sma = bt.ind.SMA(self.data0, period=15)  # 15 days sma
        # # data1 is a weekly data
        # weekly_sma = bt.ind.SMA(self.data1, period=5)  # 5 weeks sma
        #
        # self.buysig = daily_sma > weekly_sma
        self.pos = 0

    def prenext(self):
        pass

    def next(self):
        # not in the market
        idx = self.data.datetime.idx
        contract_code = self.data.p.dataname['Contract'].iloc[idx]
        print(contract_code)
        buy = self.crossover[0] > 0
        sell = self.crossover[0] < 0
        if self.pos == 1 and sell:
            # if not self.position: # if fast crosses slow to the upside
            #     self.buy(size=self.params.mult)  # enter long
            self.close(size=1, price=self.data.close[0])
            self.pos = 0

        elif self.pos == -1 and buy:
            self.close(size=1, price=self.data.close[0])
            self.pos = 0

        elif self.pos == 0 and buy:
            self.buy(size=1, price=self.data.close[0])
            self.pos = 1

        elif self.pos == 0 and sell:
            self.sell(size=1, price=self.data.close[0])
            self.pos = -1

    def notify_trade(self, trade):
        if trade.isclosed:  # 交易结束时触发
            print('交易成交记录:')
            print(f'买入日期: {trade.open_datetime()}')
            print(f'卖出日期: {trade.close_datetime()}')
            print(f'买入价格: {trade.price:.2f}')
            print(f'成交数量: {trade.size}')
            print(f'交易盈亏: {trade.pnl:.2f}')
            print(f'手续费: {trade.commission}')

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                print(
                    f'买单执行: 价格 {order.executed.price}, 成本 {order.executed.value}, 手续费 {order.executed.comm}')
            elif order.issell():
                print(
                    f'卖单执行: 价格 {order.executed.price}, 成本 {order.executed.value}, 手续费 {order.executed.comm}')
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print('订单被取消、保证金不足或拒绝')


cerebro = bt.Cerebro()  # create a "Cerebro" engine instance

# dfdata = read_data('../data/SA/SA主力连续.csv')
# dfday = transfer_period(dfdata, "D")
# dfday['date'] = pd.to_datetime(dfday.index)
# dfday['date'] = dfday['date'].apply(lambda x: x.strftime('%Y-%m-%d'))
# data = bt.feeds.PandasData(dataname=dfday)

# data = read_shfe_data("../data/MarketData_Year_2024")
# data = data[data["Contract"] == "ag2405"]
# data['Date'] = pd.to_datetime(data['Date'], format='%Y%m%d')
data = pd.read_excel("../data/MarketData_Year_2024/ag2405.xlsx")
data.set_index('Date', inplace=True)
data.rename(columns={'OI': 'OpenInterest'}, inplace=True)
data['Open'] = data['Open'].fillna(data['Close'])
data['High'] = data['High'].fillna(data['Close'])
data['Low'] = data['Low'].fillna(data['Close'])
cust_data = CustomPandasData(dataname=data)

cerebro.adddata(cust_data)  # Add the data feed

cerebro.resampledata(cust_data, timeframe=bt.TimeFrame.Weeks, compression=1)
cerebro.addstrategy(SmaCross)

cerebro.broker.setcash(10000.0)
cerebro.broker.setcommission(commission=0.00025,  # 保证金比例
                             mult=10.0,leverage=10,automargin=True,commtype=bt.CommInfoBase.COMM_PERC)
cerebro.addsizer(bt.sizers.FixedSize, stake=1)
cerebro.addanalyzer(bt.analyzers.PyFolio, _name='PyFolio', timeframe=bt.TimeFrame.Days)
# Add the trading strategy
results = cerebro.run()  # run it all
# strat = results[0]
# portfolio_stats = strat.analyzers.getbyname('PyFolio')
# returns, positions, transactions, gross_lev = portfolio_stats.get_pf_items()
# returns.index = returns.index.tz_convert(None)
#
# quantstats.reports.html(returns,output="SMA.html",title="ag2405 test report")
portval = cerebro.broker.getvalue()
print(f"剩余资金：{portval}")
cerebro.plot(style='candlestick')  # and plot it with a single command
