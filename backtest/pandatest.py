from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import argparse

import backtrader as bt
import backtrader.feeds as btfeeds

import pandas as pd


def runstrat():
    # args = parse_args()

    # Create a cerebro entity
    cerebro = bt.Cerebro(stdstats=False)

    # Add a strategy
    cerebro.addstrategy(bt.Strategy)

    # Get a pandas dataframe
    datapath = ('../data/SA/SA主力连续.csv')

    # Simulate the header row isn't there if noheaders requested

    dataframe = pd.read_csv(datapath, index_col=2, encoding='gb2312', parse_dates=True)
    dataframe.index.name = "Date"

    dataframe.rename(
        columns={"开": "Open", "高": "High", "低": "Low","收":"Close","成交量":"Volume","持仓量":"Open Interest"},
        inplace=True,
    )
    print(dataframe)


    # Pass it to the backtrader datafeed and add it to the cerebro
    data = bt.feeds.PandasData(dataname=dataframe)

    cerebro.adddata(data)

    # Run over everything
    cerebro.run()

    # Plot the result
    cerebro.plot(style='bar')


def parse_args():
    parser = argparse.ArgumentParser(
        description='Pandas test script')

    parser.add_argument('--noheaders', action='store_true', default=False,
                        required=False,
                        help='Do not use header rows')

    parser.add_argument('--noprint', action='store_true', default=False,
                        help='Print the dataframe')

    return parser.parse_args()


if __name__ == '__main__':
    runstrat()