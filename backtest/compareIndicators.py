import backtrader as bt
import quantstats
import pandas as pd
from custompandasdata import CustomPandasData


class CompareIndicatorsStrategy(bt.Strategy):
    params = (
        ('indicators', None),  # List of indicators to compare
    )

    def __init__(self):
        self.indicators_data = {}
        for ind in self.p.indicators:
            self.indicators_data[ind] = self.create_indicator(ind)
        self.orders = {ind: None for ind in self.p.indicators}
        self.trades = {ind: [] for ind in self.p.indicators}

    def create_indicator(self, ind):
        """Creates and returns a given indicator."""
        if ind == 'SMA':
            return bt.indicators.SimpleMovingAverage(self.data.close, period=10)
        elif ind == 'EMA':
            return bt.indicators.ExponentialMovingAverage(self.data.close, period=10)
        # Add more indicators as needed

    def next(self):
        """Define trading logic for each indicator."""
        for ind, indicator in self.indicators_data.items():
            if not self.orders[ind]:  # Check if there is an open order
                # Example: Buy if price crosses the moving average
                if self.data.close[0] > indicator[0]:
                    self.orders[ind] = self.buy(price=self.data.close[0])
                elif self.data.close[0] < indicator[0]:
                    self.orders[ind] = self.sell(price=self.data.close[0])
            else:
                # Track trades and close positions
                if self.orders[ind] is not None and self.orders[ind].price is not None:
                    self.trades[ind].append(self.data.close[0] - self.orders[ind].price)
                    self.orders[ind] = None

    def stop(self):
        """At the end of backtest, calculate statistics."""
        for ind in self.p.indicators:
            total_trades = len(self.trades[ind])
            winning_trades = sum(1 for trade in self.trades[ind] if trade > 0)
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            total_profit = sum(self.trades[ind])
            print(f'Indicator: {ind}, Win Rate: {win_rate:.2f}, Total Profit: {total_profit:.2f}')


# Backtest setup
if __name__ == '__main__':
    cerebro = bt.Cerebro()

    # Add data feed (e.g., CSV or Pandas DataFrame)
    data = pd.read_excel("../data/MarketData_Year_2024/ag2405.xlsx")
    data.set_index('Date', inplace=True)
    data.rename(columns={'OI': 'OpenInterest'}, inplace=True)
    data['Open'] = data['Open'].fillna(data['Close'])
    data['High'] = data['High'].fillna(data['Close'])
    data['Low'] = data['Low'].fillna(data['Close'])
    data = CustomPandasData(dataname=data)
    cerebro.adddata(data)

    # Add strategy
    indicators = ['SMA', 'EMA']  # List of indicators to compare
    cerebro.addstrategy(CompareIndicatorsStrategy, indicators=indicators)
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='PyFolio', timeframe=bt.TimeFrame.Days)

    # Run backtest
    results = cerebro.run()

    # Quantstats analysis
    strat = results[0]
    portfolio_stats = strat.analyzers.getbyname('PyFolio')
    returns, positions, transactions, gross_lev = portfolio_stats.get_pf_items()
    quantstats.reports.html(returns, output="performance_report.html")
