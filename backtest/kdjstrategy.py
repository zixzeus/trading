import backtrader as bt
import math
import pandas as pd
from custompandasdata import CustomPandasData
import quantstats


# 定义KDJ指标
class KDJ(bt.Indicator):
    lines = ('k', 'd', 'j')
    params = (('period', 14),)

    def __init__(self):
        lowest_low = bt.ind.Lowest(self.data.low, period=self.p.period)
        highest_high = bt.ind.Highest(self.data.high, period=self.p.period)

        rsv = (self.data.close - lowest_low) / (highest_high - lowest_low) * 100
        self.lines.k = bt.indicators.ExponentialMovingAverage(rsv, period=3)
        self.lines.d = bt.indicators.ExponentialMovingAverage(self.lines.k, period=3)
        self.lines.j = 3 * self.lines.k - 2 * self.lines.d


# 定义交易策略
class KDJStrategy(bt.Strategy):
    def __init__(self):
        self.kdj = KDJ()  # 引入自定义的KDJ指标
        self.order = None

    def next(self):
        if self.order:
            return  # 如果有未完成的订单，跳过交易信号

        # 买入条件：K线从下方穿过D线（金叉）
        if self.kdj.k[0] > self.kdj.d[0] and self.kdj.k[-1] <= self.kdj.d[-1]:
            self.order = self.order_target_size(target=1)

        # 卖出条件：K线从上方穿过D线（死叉）
        elif self.kdj.k[0] < self.kdj.d[0] and self.kdj.k[-1] >= self.kdj.d[-1]:
            self.order = self.order_target_size(target=-1)

    def notify_order(self, order):
        if order.status in [order.Completed]:
            self.order = None  # 重置订单状态


# 启动回测引擎
if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.addstrategy(KDJStrategy)

    # 添加数据
    data = pd.read_excel("../data/MarketData_Year_2024/ag2405.xlsx")
    data.set_index('Date', inplace=True)
    data.rename(columns={'OI': 'OpenInterest'}, inplace=True)
    data['Open'] = data['Open'].fillna(data['Close'])
    data['High'] = data['High'].fillna(data['Close'])
    data['Low'] = data['Low'].fillna(data['Close'])
    data = CustomPandasData(dataname=data)
    cerebro.adddata(data)

    # 设置初始资金
    cerebro.broker.setcash(10000.0)

    # 设置每次交易的买卖规模
    cerebro.broker.setcommission(commission=0.00025,  # 保证金比例
                                 mult=10.0, leverage=10, automargin=True, commtype=bt.CommInfoBase.COMM_PERC)
    cerebro.addsizer(bt.sizers.FixedSize, stake=1)
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='PyFolio', timeframe=bt.TimeFrame.Days)

    # 开始回测
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    results = cerebro.run()
    print('Ending Portfolio Value: %.2f' % cerebro.broker.getvalue())
    strat = results[0]
    portfolio_stats = strat.analyzers.getbyname('PyFolio')
    returns, positions, transactions, gross_lev = portfolio_stats.get_pf_items()
    quantstats.reports.html(returns, output="kdj_performance_report.html")
    # 可视化K线图
    cerebro.plot(style='candlestick')
