import akshare as ak
import pandas as pd
import numpy as np
from scipy.stats import linregress
from datetime import datetime
import matplotlib.pyplot as plt


# Fetch daily futures data for a specific contract, e.g., "RB" (rebar) from the Shanghai Futures Exchange (SHFE)
# https://akshare.akfamily.xyz/data/futures/futures.html#id57


def get_current_term_structures(symbol):
    future_zh_realtime_df = ak.futures_zh_realtime(symbol=symbol)
    df_sorted = future_zh_realtime_df.sort_values(by=['symbol']).reset_index(drop=True)
    prices = df_sorted.iloc[1:]['trade']
    if len(prices) < 2:
        return None, None
    else:
        x = np.arange(len(prices))
        if prices.dtype == 'object':
            prices = pd.to_numeric(prices, errors='coerce')
        slope, intercept, r_value, p_value, std_err = linregress(x, prices)
    if slope < 0:
        structure = "Backwardation"
    elif slope > 0:
        structure = "Contango"
    else:
        structure = "Flat"
    return structure, slope


def traversal_all_futures_structures():
    futures_symbol_mark_df = ak.futures_symbol_mark()

    big_df = pd.DataFrame()
    for item in futures_symbol_mark_df['symbol']:
        structure, slope = get_current_term_structures(item)
        data = [
            [item, structure, slope]
        ]
        new_df = pd.DataFrame(data, columns=['symbol', 'structure', 'slope'])
        big_df = pd.concat([big_df, new_df], ignore_index=True)

    return big_df


# futures_zh_daily_sina_df = ak.futures_zh_daily_sina(symbol="RB0")
# print(futures_zh_daily_sina_df)
#
def traversal_hist_futures_structures(start_date="20230101", end_date="20241113", market="CZCE"):
    # for market in {"CZCE", "DCE", "SHFE", "GFEX"}:
    futures_hist_df = ak.get_futures_daily(start_date=start_date, end_date=end_date, market=market)
    symbols = futures_hist_df['variety'].unique()
    for symbol in symbols:
        hist_df = futures_hist_df[futures_hist_df['variety'] == symbol]
        dates = futures_hist_df.date.drop_duplicates()
        big_df = pd.DataFrame()
        for date in dates:
            daily_df = hist_df[hist_df['date'] == date]
            df_sorted = daily_df.sort_values(by=['symbol']).reset_index(drop=True)
            prices = df_sorted['settle']
            if len(prices) >= 2:
                x = np.arange(len(prices))
                if prices.dtype == 'object':
                    prices = pd.to_numeric(prices, errors='coerce')
                slope, intercept, r_value, p_value, std_err = linregress(x, prices)
                if slope < 0:
                    structure = "Backwardation"
                elif slope > 0:
                    structure = "Contango"
                else:
                    structure = "Flat"
                symbol = daily_df.variety.iloc[0]
                max_volume_index = df_sorted['volume'].idxmax()
                max_volume_price = df_sorted.loc[max_volume_index, 'settle']
                data = [
                    [date, symbol, structure, slope, max_volume_price]
                ]
                new_df = pd.DataFrame(data, columns=['date', 'symbol', 'structure', 'slope', 'max_volume_price'])
                big_df = pd.concat([big_df, new_df], ignore_index=True)
        #     print(daily_df)
        # print(dates)
        print(big_df)
        current_date = datetime.now().date()
        big_df.to_excel(f'../data/{symbol}_hist_structure_{current_date}.xlsx')


def plot_the_term(file):
    sa_structure = pd.read_excel(file, parse_dates=True, index_col=0)
    # sa_structure.drop(index=[0])
    sa_structure['date'] = pd.to_datetime(sa_structure['date'], format='%Y%m%d')
    print(sa_structure)
    plt.figure(figsize=(10, 5))
    fig, ax1 = plt.subplots(figsize=(12, 6))

    ax1.plot(sa_structure['date'], sa_structure['max_volume_price'], color='blue', marker='o', label='price',
             linewidth=2)
    ax1.set_xlabel('date', fontsize=12)
    ax1.set_ylabel('price', color='blue', fontsize=12)
    ax1.tick_params(axis='y', labelcolor='blue')

    ax1.grid(axis='both', linestyle='--', alpha=0.7)

    # 绘制成交量曲线（右轴）
    ax2 = ax1.twinx()
    # ax2.bar(sa_structure['date'], df['成交量'], alpha=0.6, label='成交量', color='gray', width=0.5)
    ax2.plot(sa_structure['date'], sa_structure['slope'], color='green', marker='x', linestyle='--', label='slope',
             linewidth=2)
    ax2.set_ylabel('slope', color='black', fontsize=12)
    ax2.tick_params(axis='y', labelcolor='black')


# 添加图例
    ax1.legend(loc='upper left')
    ax2.legend(loc='upper right')

    # 调整布局
    plt.title('term structure', fontsize=14)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    symbol = "纯碱"
    current_date = datetime.now().date()
    get_current_term_structures(symbol)
    # structure_df = traversal_all_futures_structures()
    # print(structure_df)
    # structure_df.to_excel(f'../data/structure_df_{current_date}.xlsx')

    # formatted_date = current_date.strftime("%Y%m%d")
    # traversal_hist_futures_structures(market="SHFE")
    file = '../data/RB_hist_structure_2024-11-17.xlsx'
    plot_the_term(file)
