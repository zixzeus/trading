import backtrader as bt
import pandas as pd
from custompandasdata import CustomPandasData
import quantstats
from utils.basic import read_czce_futures_txt, read_czce_options_txt
from datetime import datetime, timedelta

DEBUG = False


def calculate_profit_ratio(row, atm_call_price, atm_put_price):
    if row['Delta'] > 0:
        return atm_call_price / row['Close'] if atm_call_price > 0 else None
    elif row['Delta'] < 0:
        return atm_put_price / row['Close'] if atm_put_price > 0 else None


class OptionFuturesStrategy(bt.Strategy):
    params = (
        ('long_strike', 100),  # 买入看涨期权的行权价
        ('short_strike', 105),  # 卖出看涨期权的行权价
        ('expiry_date', None),  # 期权到期日期
        ('pfast', 5),  # period for the fast moving average
        ('pslow', 10),  # period for the slow moving average
        ('mult', 10),
        ('hold_days', 1),
        ('period', 10),
        ('stop_loss', 0.03),
    )

    def __init__(self):
        # 使用第一个数据（期货数据）作为标的资产

        self.futures_data = self.datas[0]
        # 使用第二个数据（期权数据）作为期权
        self.options_data = self.datas[-1]
        self.options = {}
        self.open_times = {}
        self.avg_volume = {}
        contracts_code = self.options_data.p.dataname["合约代码"].drop_duplicates()
        for contract in contracts_code:
            self.options[contract] = self.getdatabyname(contract)
            self.avg_volume[contract] = bt.indicators.SimpleMovingAverage(self.options[contract].volume,
                                                                          period=self.params.period)

        sma1 = bt.ind.SMA(self.futures_data.close, period=self.p.pfast)  # fast moving average
        sma2 = bt.ind.SMA(self.futures_data.close, period=self.p.pslow)
        self.crossover = bt.ind.CrossOver(sma1, sma2)
        # 持有期权的状态变量
        self.long_option = None
        self.short_option = None
        self.call = None
        self.put = None

    def next(self):
        # 获取当前期货价格和期权价格
        buy = self.crossover[0] > 0
        sell = self.crossover[0] < 0
        current_date = pd.Timestamp(self.options_data.datetime.date(0))
        futures_price = self.futures_data.close[0]
        option_price = self.options_data.close[0]
        idx2 = self.options_data.datetime.idx
        option_code = self.options_data.p.dataname.iloc[idx2]["合约代码"]
        options = self.options_data.p.dataname.loc[current_date].copy()
        options = options.loc[(options['Close'] != 0) & (options['Volume'] > 10)]

        # options = options.loc[(options['Close'] != 0)]
        if options.empty:
            return
        call_atm_index = (options['Delta'] - 0.5).abs().argmin()
        call_atm_price = options["Close"].iloc[call_atm_index]

        put_atm_index = (options['Delta'] + 0.5).abs().argmin()
        put_atm_price = options["Close"].iloc[put_atm_index]

        options['pl_ratio'] = options.apply(calculate_profit_ratio, axis=1, args=(call_atm_price, put_atm_price))
        # options['Kelly'] = ((options['pl_ratio'] + 1) * abs(options['Delta']) - 1) / options['pl_ratio']
        options['Kelly'] = options.apply(
            lambda row: ((row['pl_ratio'] + 1) * row['Delta'] - 1) / row['pl_ratio'] if row['Delta'] > 0 else
            ((row['pl_ratio'] + 1) * row['Delta'] + 1) / row['pl_ratio'],
            axis=1
        )
        call_options = options.loc[options['Delta'] > 0, 'Kelly']
        put_options = options.loc[options['Delta'] < 0, 'Kelly']
        top5_call = call_options.nlargest(3)
        top5_put = put_options.nsmallest(3)
        if self.options_data.Delta[0] > 0:
            if self.options_data.close[0] == 0:
                return
            pl_ratio = call_atm_price / self.options_data.close[0]
            win_ratio = self.options_data.Delta[0]
            kelly_fraction = ((pl_ratio + 1) * win_ratio - 1) / pl_ratio
            if pl_ratio * win_ratio > 1 and kelly_fraction > top5_call.iloc[-1] and self.options_data.volume[0] > 2 * \
                    self.avg_volume[option_code][0]:
                cash = self.broker.getcash()
                if cash > 0:
                    position_size = cash * kelly_fraction
                    self.call = self.buy(data=self.options[option_code], price=self.options_data.close[0],
                                         size=position_size / self.options_data.close[0])
                    self.sell(exectype=bt.Order.Stop, price=self.options_data.close[0] * (1 - self.params.stop_loss))
                    self.open_times[option_code] = self.options[option_code].datetime.datetime(0)
                if DEBUG:
                    print(
                        f"{current_date}buy Call Option {option_code} at price {option_price} (futures price: {futures_price})")

        elif self.options_data.Delta[0] < 0:
            if self.options_data.close[0] == 0:
                return
            pl_ratio = put_atm_price / self.options_data.close[0]
            win_ratio = self.options_data.Delta[0]
            kelly_fraction = ((pl_ratio + 1) * win_ratio + 1) / pl_ratio
            if pl_ratio * win_ratio < -1 and kelly_fraction < top5_put.iloc[-1] and self.options_data.volume[0] > 2 * \
                    self.avg_volume[option_code][0]:
                cash = self.broker.getcash()
                if cash > 0:
                    position_size = cash * abs(kelly_fraction)*0.05
                    self.put = self.buy(data=self.options[option_code], price=self.options_data.close[0],
                                        size=position_size / self.options_data.close[0])
                    self.sell(exectype=bt.Order.Stop, price=self.options_data.close[0] * (1 - self.params.stop_loss))
                    self.open_times[option_code] = self.options[option_code].datetime.datetime(0)
                if DEBUG:
                    print(
                        f"{current_date} buy put Option {option_code} at price {option_price} (futures price: {futures_price})")

        for contract, data in self.options.items():
            # 获取期权的持仓
            position = self.getposition(data)
            # print(position)
            # 基于期货价格做决策
            # positions = self.getposition(self.options)
            if position:
                if self.open_times.get(contract) is None:
                    print(contract)
                time_diff = data.datetime.date() - self.open_times.get(contract).date()
                hold_enough_time = time_diff == timedelta(days=self.params.hold_days)

                if hold_enough_time:
                    self.close(data)
                    del self.open_times[contract]
                    if DEBUG:
                        print(
                            f"{current_date} Close Option {contract} at price {data.close[0]} (futures price: {futures_price})")  # 使用期权数据卖出看涨期权
                # if (hold_enough_time
                #                 and (buy
                #                                  and
                #                                  ((options.loc[options['合约代码'] == contract, 'Kelly'] < 0) & (
                #                                          options.loc[options['合约代码'] == contract, 'Delta'] > 0)).all()
                #         )
                # ):
                #     if DEBUG:
                #         print(
                #         f"{current_date} Close Put Option {contract} at price {data.close[0]} (futures price: {futures_price})")  # 使用期权数据买入看涨期权
                #     self.close(data)
                #     del self.open_times[contract]
                # elif (hold_enough_time
                #               and (sell
                #                                    and
                #                                    ((options.loc[options['合约代码'] == contract, 'Kelly'] > 0) & (
                #                 options.loc[options['合约代码'] == contract, 'Delta'] < 0)).all()
                #         )
                # ):
                #     if DEBUG:
                #         print(
                #         f"{current_date} Close Call Option {contract} at price {data.close[0]} (futures price: {futures_price})")  # 使用期权数据卖出看涨期权
                #     self.close(data)
                #     del self.open_times[contract]

        # 在期权到期日清仓
        # if self.p.expiry_date and self.futures_data.datetime.date(0) >= self.p.expiry_date:
        #     if self.long_option:
        #         print("Closing long option position")
        #         self.close(self.long_option)
        #     if self.short_option:
        #         print("Closing short option position")
        #         self.close(self.short_option)

    # def notify_trade(self, trade):
    #     if trade.isclosed:  # 交易结束时触发
    #         print('交易成交记录:')
    #         print(f'买入日期: {trade.open_datetime()}')
    #         print(f'卖出日期: {trade.close_datetime()}')
    #         print(f'买入价格: {trade.price:.2f}')
    #         print(f'成交数量: {trade.size}')
    #         print(f'交易盈亏: {trade.pnl:.2f}')
    #         print(f'手续费: {trade.commission}')

    def notify_order(self, order):
        if DEBUG:
            if order.status in [order.Completed]:
                if order.isbuy():
                    print(
                        f'买单执行: 价格 {order.executed.price}, 成本 {order.executed.value}, 手续费 {order.executed.comm}')
                elif order.issell():
                    print(
                        f'卖单执行: 价格 {order.executed.price}, 成本 {order.executed.value}, 手续费 {order.executed.comm}')
            elif order.status in [order.Canceled, order.Margin, order.Rejected]:
                print('订单被取消、保证金不足或拒绝')

    def stop(self):
        print('(Hold Days %2d) Ending Value %.2f' %
              (self.params.hold_days, self.broker.getvalue()))


if __name__ == "__main__":
    # 创建 Cerebro 实例
    cerebro = bt.Cerebro()

    # 加载期货数据
    contract_name = "SA406"
    # futures_df = read_czce_futures_txt('../data/CZCE/ALLFUTURES2024.txt')
    # futures_df.to_csv('../data/CZCE/ALLFUTURES2024.csv')
    futures_df = pd.read_csv("../data/CZCE/ALLFUTURES2024.csv")
    futures_df["交易日期"] = pd.to_datetime(futures_df["交易日期"])
    futures_df.set_index('交易日期', inplace=True)
    futures_df = futures_df[futures_df["合约代码"].str.contains(contract_name)]
    futures_data = CustomPandasData(dataname=futures_df)
    # 加载期权数据（假设使用另一个股票来模拟期权数据）
    # options_df = read_czce_options_txt('../data/CZCE/ALLOPTIONS2024.txt')
    # options_df.to_csv("../data/CZCE/ALLOPTIONS2024.csv")
    options_df = pd.read_csv("../data/CZCE/ALLOPTIONS2024.csv")
    options_df["交易日期"] = pd.to_datetime(options_df["交易日期"])
    options_df.set_index('交易日期', inplace=True)
    options_df = options_df[options_df["合约代码"].str.contains(contract_name)]
    options_data = CustomPandasData(dataname=options_df)
    # 添加期货和期权数据到 cerebro
    cerebro.adddata(futures_data, name="Futures")

    options_code = options_df["合约代码"].drop_duplicates()
    for contract in options_code:
        option_df = options_df[options_df['合约代码'] == contract]
        option_data = CustomPandasData(dataname=option_df)
        cerebro.adddata(option_data, name=contract)

    cerebro.adddata(options_data, name="Option")

    # 添加策略
    # cerebro.addstrategy(OptionFuturesStrategy,hold_days=13)
    cerebro.optstrategy(
        OptionFuturesStrategy,
        hold_days=range(1, 31))
    # 设置初始现金
    cerebro.broker.set_cash(10000)
    cerebro.broker.set_coc(True)
    cerebro.broker.setcommission(commission=0.00025,  # 保证金比例
                                 mult=10.0, leverage=10, automargin=True, commtype=bt.CommInfoBase.COMM_PERC)
    cerebro.addsizer(bt.sizers.FixedSize, stake=1)
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='PyFolio', timeframe=bt.TimeFrame.Days)
    # 启动回测
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    results = cerebro.run(maxcpus=1)
    print('Ending Portfolio Value: %.2f' % cerebro.broker.getvalue())
    # for res in results:
    #     print('最终资金: %.2f' % res.broker.getvalue())
    # strat = results[0]
    # portfolio_stats = strat.analyzers.getbyname('PyFolio')
    # returns, positions, transactions, gross_lev = portfolio_stats.get_pf_items()
    # returns.index = returns.index.tz_convert(None)
    #
    # quantstats.reports.html(returns, output="option_trading_new.html", title="SA2406 test report")
    # 绘制图形
    # cerebro.plot(style='candlestick')
