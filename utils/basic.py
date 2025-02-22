# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

import pandas as pd
# ts.set_token('fe9769b100b23f917db80c4a55c5b5fb9440dd4ede6e4d7af1073a85')
# pro = ts.pro_api('fe9769b100b23f917db80c4a55c5b5fb9440dd4ede6e4d7af1073a85')
# df = pro.daily(trade_date='20200325')
# print(df)

import matplotlib.pyplot as plt
import mplfinance as mpf
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import talib
from mplfinance.original_flavor import candlestick2_ochl
import os, sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
folder_path = "./data/"


def read_data(file_name):
    data = pd.read_csv(file_name, index_col=2, encoding='gb2312', parse_dates=True)
    data.index.name = "Date"

    data.rename(
        columns={"开": "Open", "高": "High", "低": "Low", "收": "Close", "成交量": "Volume", "持仓量": "OpenInterest"},
        inplace=True,
    )
    return data


def read_shfe_data(folder_path):
    files_list = os.listdir(folder_path)
    df_list = []
    for file in files_list:
        if file.startswith("所内") and file.endswith('.xls'):
            monthly_data = pd.read_excel(f"{folder_path}/{file}", skiprows=3, skipfooter=5)
            monthly_data.drop(monthly_data.columns[-1], axis=1, inplace=True)
            monthly_data['Contract'] = monthly_data['Contract'].ffill()
            df_list.append(monthly_data)

    merged_df = pd.concat(df_list, ignore_index=True)
    return merged_df


def read_czce_futures_txt(file_path):
    futures_df = pd.read_table(file_path, skiprows=1, sep="|", low_memory=False)
    futures_df.columns = [col.rstrip() for col in futures_df.columns]
    futures_df.rename(
        columns={'今开盘': 'Open', '最高价': 'High', '最低价': 'Low', '今收盘': 'Close', '成交量(手)': 'Volume',
                 '持仓量': 'OpenInterest'},
        inplace=True)
    if '交易日期' in futures_df.columns:
        futures_df.set_index('交易日期', inplace=True)
        futures_df.index = pd.to_datetime(futures_df.index)
    futures_df.iloc[:, 0] = futures_df.iloc[:, 0].apply(
        lambda x: x.rstrip())
    futures_df.iloc[:, 1:] = futures_df.iloc[:, 1:].apply(
        lambda x: x.astype(str).str.replace(',', '').apply(pd.to_numeric, errors='coerce'))
    return futures_df


def read_czce_options_txt(file_path):
    options_df = pd.read_table(file_path, skiprows=1, sep="|", low_memory=False)
    options_df.columns = [col.rstrip() for col in options_df.columns]
    options_df.rename(
        columns={'今开盘': 'Open', '最高价': 'High', '最低价': 'Low', '今收盘': 'Close', '成交量(手)': 'Volume',
                 '持仓量': 'OpenInterest', 'DELTA': 'Delta'},
        inplace=True)
    if '交易日期' in options_df.columns:
        options_df.set_index('交易日期', inplace=True)
        options_df.index = pd.to_datetime(options_df.index)
    options_df.iloc[:, 1:] = options_df.iloc[:, 1:].apply(
        lambda x: x.astype(str).str.replace(',', '').apply(pd.to_numeric, errors='coerce'))
    return options_df


def detect_pattern(pattern, pattern_name, df):
    df[pattern_name] = pattern(df["Open"].values, df["High"].values, df["Low"].values,
                               df["Close"].values)
    dfpattern = df[(df[pattern_name] == 100) | (dfday[pattern_name] == -100)]
    return dfpattern


def show_pattern(dfday, pattern, pattern_name, save=False):
    fig = plt.figure(figsize=(16, 9))
    plt.rcParams['font.sans-serif'] = ['SimHei']
    ax = fig.add_subplot()
    # mpf.plot(dfday, type="candle",volume=True)
    candlestick2_ochl(ax, dfday["Open"], dfday["Close"], dfday["High"], dfday["Low"], width=0.6, colorup='r',
                      colordown='green',
                      alpha=1.0)

    for index, today in pattern.iterrows():
        x_posit = dfday.index.get_loc(index)
        ax.annotate("{},{}".format(pattern_name, today["date"]), xy=(x_posit, today["High"]),
                    xytext=(0, 10), xycoords="data",
                    fontsize=18, textcoords="offset points", arrowprops=dict(arrowstyle="simple", color="r"))

    ax.xaxis.set_major_locator(ticker.MaxNLocator(2))

    def format_date(x, pos=None):
        if x < 0 or x > len(dfday['date']) - 1:
            return ''
        return dfday['date'].iloc[int(x)]

    ax.xaxis.set_major_formatter(ticker.FuncFormatter(format_date))
    plt.setp(plt.gca().get_xticklabels(), rotation=45, horizontalalignment='right')
    if save == True and not os.path.exists(f"{pattern_name}.png"):
        plt.savefig(f"../pictures/{pattern_name}.png", dpi=600)
    plt.show()


def transfer_period(df_1min, period):
    if period in ["D", "W", "M"]:
        dfnew = df_1min.resample(period).agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum",
            "OpenInterest": "last"
        }).dropna()
    elif period in ["H", "30min"]:
        dfnew = df_1min.resample(period, closed='right', label='right').agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum",
            "OpenInterest": "last"
        }).dropna()

    return dfnew


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    data = read_data('../data/SA/SA主力连续.csv')
    dfday = transfer_period(data, "D")
    dfday['date'] = pd.to_datetime(dfday.index)
    dfday['date'] = dfday['date'].apply(lambda x: x.strftime('%Y-%m-%d'))

    pattern_name = "hangingman"
    pattern = detect_pattern(talib.CDLHANGINGMAN, pattern_name, dfday)
    print(pattern)

    show_pattern(dfday, pattern, pattern_name, True)
    import time

    start_time1 = time.time()
    big_df = read_shfe_data('../data/MarketData_Year_2024')
    # print(big_df)
    end_time1 = time.time()
    execution_time1 = end_time1 - start_time1
    print(f"Execution time: {execution_time1} seconds")

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
