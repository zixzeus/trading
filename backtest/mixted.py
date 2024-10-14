import pandas as pd
import numpy as np
import datetime
import backtrader as bt
from custompandasdata import CustomPandasData


# 定义Observer
class OrderObserver(bt.observer.Observer):
    lines = ('created', 'expired',)
    # 做图参数设置
    plotinfo = dict(plot=True, subplot=True, plotlinelabels=True)
    # 创建工单 * 标识，过期工单 方块 标识
    plotlines = dict(
        created=dict(marker='*', markersize=8.0, color='lime', fillstyle='full'),
        expired=dict(marker='s', markersize=8.0, color='red', fillstyle='full')
    )

    # 处理 Lines
    def next(self):
        for order in self._owner._orderspending:
            if order.data is not self.data:
                continue

            if not order.isbuy():
                continue

            # Only interested in "buy" orders, because the sell orders
            # in the strategy are Market orders and will be immediately
            # executed

            if order.status in [bt.Order.Accepted, bt.Order.Submitted]:
                self.lines.created[0] = order.created.price

            elif order.status in [bt.Order.Expired]:
                self.lines.expired[0] = order.created.price


# 定义策略
class MACD_KDJStrategy(bt.Strategy):
    # 策略参数
    params = (
        ('highperiod', 9),
        ('lowperiod', 9),
        ('kperiod', 3),
        ('dperiod', 3),
        ('me1period', 12),
        ('me2period', 26),
        ('signalperiod', 9),
        ('limitperc', 1.0),  # 限价比例 ，下跌1个百分点才买入，目的可以展示Observer的过期单
        ('valid', 7),  # 限价周期
        ('print', False),
        ('counter', 0),  # 计数器
    )

    def log(self, txt, dt=None):
        """ Logging function fot this strategy"""
        dt = dt or self.datas[0].datetime.date(0)
        if self.params.print:
            print("%s, %s" % (dt.isoformat(), txt))

    def __init__(self):
        # 初始化全局变量，备用
        self.dataclose = self.datas[0].close
        self.dataopen = self.datas[0].open
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        self.volume = self.datas[0].volume

        self.order = None
        self.buyprice = None
        self.buycomm = None

        # N个交易日内最高价
        self.highest = bt.indicators.Highest(self.data.high, period=self.p.highperiod)
        # N个交易日内最低价
        self.lowest = bt.indicators.Lowest(self.data.low, period=self.p.lowperiod)

        # 计算rsv值 RSV=(CLOSE- LOW) / (HIGH-LOW) * 100
        # 如果被除数0 ，为None
        self.rsv = 100 * bt.DivByZero(
            self.data_close - self.lowest, self.highest - self.lowest, zero=None
        )

        # 计算rsv的N个周期加权平均值，即K值
        self.K = bt.indicators.EMA(self.rsv, period=self.p.kperiod, plot=False)
        # D值=K值 的N个周期加权平均值
        self.D = bt.indicators.EMA(self.K, period=self.p.dperiod, plot=False)
        # J=3*K-2*D
        self.J = 3 * self.K - 2 * self.D

        # MACD策略参数
        me1 = bt.indicators.EMA(self.data, period=self.p.me1period, plot=True)
        me2 = bt.indicators.EMA(self.data, period=self.p.me2period, plot=True)

        self.macd = me1 - me2
        self.signal = bt.indicators.EMA(self.macd, period=self.p.signalperiod)
        bt.indicators.MACDHisto(self.data)

    # 订单通知处理
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    "BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f"
                    % (order.executed.price, order.executed.value, order.executed.comm)
                )

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
                self.bar_executed_close = self.dataclose[0]
            else:
                self.log(
                    "SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f"
                    % (order.executed.price, order.executed.value, order.executed.comm)
                )
            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log("Order Canceled/Margin/Rejected")

        self.order = None

    # 交易通知处理
    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log("OPERATION PROFIT, GROSS %.2f, NET %.2f" % (trade.pnl, trade.pnlcomm))

    # 策略执行
    def next(self):
        self.log("Close, %.2f" % self.dataclose[0])
        if self.order:
            return

        # 空仓中，开仓买入
        if not self.position:
            # 买入基于MACD策略
            condition1 = self.macd[-1] - self.signal[-1]  # 昨天低于signal
            condition2 = self.macd[0] - self.signal[0]  # 今天高于signal
            # 买入基于KDJ策略 K值大于D值，K线向上突破D线时，为买进信号。下跌趋势中，K值小于D值，K线向下跌破D线时，为卖出信号。
            condition3 = self.K[-1] - self.D[-1]  # 昨天J低于D
            condition4 = self.K[0] - self.D[0]  # 今天J高于D

            if condition1 < 0 and condition2 > 0 and condition3 < 0 and condition4 > 0:
                self.log('BUY CREATE, %.2f' % self.dataclose[0])

                plimit = self.data.close[0] * (1.0 - self.p.limitperc / 100.0)
                valid = self.data.datetime.date(0) + datetime.timedelta(days=self.p.valid)
                self.log('BUY CREATE, %.2f' % plimit)
                # 限价购买
                self.buy(exectype=bt.Order.Limit, price=plimit, valid=valid)


        else:
            # 卖出基于MACD策略
            condition1 = self.macd[-1] - self.signal[-1]
            condition2 = self.macd[0] - self.signal[0]
            # 卖出基于KDJ策略
            condition3 = self.K[-1] - self.D[-1]
            condition4 = self.D[0] - self.D[0]

            if condition1 > 0 and condition2 < 0 and (condition3 > 0 or condition4 < 0):
                self.log("SELL CREATE, %.2f" % self.dataclose[0])
                self.order = self.sell()

    def start(self):
        # 从0 开始
        # self.params.counter += 1
        self.log('Strategy start %s' % self.params.counter)

    def nextstart(self):
        self.params.counter += 1
        self.log('Strategy nextstart %s' % self.params.counter)

    def prenext(self):
        self.params.counter += 1
        self.log('Strategy prenext  %s' % self.params.counter)

    def stop(self):
        self.params.counter += 1
        self.log('Strategy stop  %s' % self.params.counter)
        self.log('Ending Value %.2f' % (self.broker.getvalue()))


if __name__ == "__main__":
    tframes = dict(
        days=bt.TimeFrame.Days,
        weeks=bt.TimeFrame.Weeks,
        months=bt.TimeFrame.Months,
        years=bt.TimeFrame.Years)

    #1.实例初始化
    cerebro = bt.Cerebro()

    # 2.加载数据 Data feeds
    # 加载数据到模型中，由dataframe 到 Lines 数据类型，查询10年数据到dataframe
    data = pd.read_excel("../data/MarketData_Year_2024/ag2405.xlsx")
    data.set_index('Date', inplace=True)
    data.rename(columns={'OI': 'OpenInterest'}, inplace=True)
    data['Open'] = data['Open'].fillna(data['Close'])
    data['High'] = data['High'].fillna(data['Close'])
    data['Low'] = data['Low'].fillna(data['Close'])
    data = CustomPandasData(dataname=data)
    # bt加载数据
    cerebro.adddata(data)

    #3.加载策略 Strategy
    cerebro.addstrategy(MACD_KDJStrategy)

    #4.加载分析器 Analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='mysharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='mydrawdown')
    cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='myannualreturn')

    #5.加载观察者 Observers
    cerebro.addobserver(OrderObserver)

    #6.设置仓位管理 Sizers
    cerebro.addsizer(bt.sizers.FixedSize, stake=100)

    #7.设置佣金管理 Commission
    cerebro.broker.setcommission(commission=0.002)

    #8.设置初始资金
    cerebro.broker.setcash(100000)
    print("Starting Portfolio Value: %.2f" % cerebro.broker.getvalue())

    #9.启动回测
    checkstrats = cerebro.run()
    #数据源0 返回值处理
    checkstrat = checkstrats[0]

    #10.回测结果
    print("Final Portfolio Value: %.2f" % cerebro.broker.getvalue())

    print('夏普率:')
    for k, v in checkstrat.analyzers.mysharpe.get_analysis().items():
        print(k, ':', v)

    print('最大回测:')
    for k, v in checkstrat.analyzers.mydrawdown.get_analysis()['max'].items():
        print('max ', k, ':', v)

    print('年化收益率:')
    for year, ann_ret in checkstrat.analyzers.myannualreturn.get_analysis().items():
        print(year, ':', ann_ret)

    #11.回测图示
    cerebro.plot()
