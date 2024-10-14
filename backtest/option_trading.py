import backtrader as bt
import pandas as pd
from custompandasdata import CustomPandasData
# import quantstats
from utils.basic import read_czce_futures_txt, read_czce_options_txt


class OptionFuturesStrategy(bt.Strategy):
    params = (
        ('long_strike', 100),  # 买入看涨期权的行权价
        ('short_strike', 105),  # 卖出看涨期权的行权价
        ('expiry_date', None),  # 期权到期日期
        ('pfast', 5),  # period for the fast moving average
        ('pslow', 10),  # period for the slow moving average
        ('mult', 10),
    )

    def __init__(self):
        # 使用第一个数据（期货数据）作为标的资产

        self.futures_data = self.datas[1]
        # 使用第二个数据（期权数据）作为期权
        self.options_data = self.datas[0]
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
        current_data = pd.Timestamp(self.options_data.datetime.date(0))
        futures_price = self.futures_data.close[0]
        option_price = self.options_data.close[0]
        # print(current_data)
        # print(self.options_data.datetime.date(0))
        # print(self.data.datetime.date(0))
        idx = self.futures_data.datetime.idx
        idx2 = self.options_data.datetime.idx
        option_code = self.options_data.p.dataname.iloc[idx2]["合约代码"]
        options = self.options_data.p.dataname.loc[current_data, "Delta"]
        call_atm_index = (options - 0.5).abs().argmin()
        call_atm_price = self.options_data.p.dataname.loc[current_data, "Close"].iloc[call_atm_index]

        put_atm_index = (options + 0.5).abs().argmin()
        put_atm_price = self.options_data.p.dataname.loc[current_data, "Close"].iloc[put_atm_index]

        if self.options_data.Delta[0] > 0:
            if self.options_data.close[0] == 0:
                return
            pl_ratio = call_atm_price / self.options_data.close[0]
            win_ratio = self.options_data.Delta[0]
            if pl_ratio * win_ratio > 1:
                self.call = self.buy(price=self.options_data.close[0], size=1, volume=1)
                print(f"buy Call Option {option_code} at price {option_price} (futures price: {futures_price})")

        elif self.options_data.Delta[0] < 0:
            if self.options_data.close[0] == 0:
                return
            pl_ratio = put_atm_price / self.options_data.close[0]
            win_ratio = self.options_data.Delta[0]
            if pl_ratio * win_ratio < -1:
                self.put = self.buy(price=self.options_data.close[0], size=1, volume=1)
                print(f"buy put Option {option_code} at price {option_price} (futures price: {futures_price})")

        # print(call_atm_price)
        # print(options)
        # print(self.options_data.p.dataname.iloc[idx2]["Close"])
        # option_price = self.options_data.close[0]
        #
        # print(option_price)
        #
        # print("futures")
        # print(self.futures_data.p.dataname.iloc[idx]["Close"])
        # future_price = self.futures_data.close[0]
        # print(future_price)
        # print(idx)
        # print(idx2)
        # print(self.data.p.dataname["合约代码"].iloc[idx])
        # print(self.options_data.p.dataname.iloc[idx2]["合约代码"])
        # print(self.futures_data.p.dataname.loc[current_data, "合约代码"])
        # print(self.options_data.p.dataname.loc[current_data, "合约代码"])

        # print("future price is:", futures_price)
        # print("option price is:", option_price)

        # 基于期货价格做决策
        if buy and self.position:
            print(f"Close Call Option {option_code} at price {option_price} (futures price: {futures_price})") # 使用期权数据买入看涨期权
            self.close(self.options_data)

        if sell and self.position:
            print(f"Close Call Option {option_code} at price {option_price} (futures price: {futures_price})")# 使用期权数据卖出看涨期权
            self.close(self.options_data)

        # 在期权到期日清仓
        # if self.p.expiry_date and self.futures_data.datetime.date(0) >= self.p.expiry_date:
        #     if self.long_option:
        #         print("Closing long option position")
        #         self.close(self.long_option)
        #     if self.short_option:
        #         print("Closing short option position")
        #         self.close(self.short_option)

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


if __name__ == "__main__":
    # 创建 Cerebro 实例
    cerebro = bt.Cerebro()

    # 加载期货数据
    contract_name = "SA405"
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
    cerebro.adddata(options_data, name="Option")
    cerebro.adddata(futures_data, name="Futures")


    # 添加策略
    cerebro.addstrategy(OptionFuturesStrategy)

    # 设置初始现金
    cerebro.broker.set_cash(1000000)
    cerebro.broker.setcommission(commission=0.00025,  # 保证金比例
                                 mult=10.0, leverage=10, automargin=True, commtype=bt.CommInfoBase.COMM_PERC)
    cerebro.addsizer(bt.sizers.FixedSize, stake=1)
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='PyFolio', timeframe=bt.TimeFrame.Days)
    # 启动回测
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    results = cerebro.run()
    print('Ending Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # strat = results[0]
    # portfolio_stats = strat.analyzers.getbyname('PyFolio')
    # returns, positions, transactions, gross_lev = portfolio_stats.get_pf_items()
    # returns.index = returns.index.tz_convert(None)
    #
    # quantstats.reports.html(returns,output="option_trading.html",title="SA2405 test report")
    # 绘制图形
    cerebro.plot(style='candlestick')
