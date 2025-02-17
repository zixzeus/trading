import os
import sys

import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd
from utils.basic import read_czce_futures_txt,read_czce_options_txt

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

folder_path = "../data/CZCE/"
files_list = os.listdir(f"{folder_path}/ALLOPTIONS2024/")


def transfer_file():
    for file in files_list:
        if file.endswith('2024.txt'):
            option = read_czce_options_txt(f"{folder_path}/ALLOPTIONS2024/{file}")
            option_csv_name = file.replace(".txt",".csv")
            option.to_csv(f"{folder_path}/ALLOPTIONS2024/{option_csv_name}")
            future_name = file.replace("OPTIONS", "FUTURES")
            future = read_czce_futures_txt(f"{folder_path}/ALLFUTURES2024/{future_name}")
            future_csv_name = future_name.replace(".txt",".csv")
            future.to_csv(f"{folder_path}/ALLFUTURES2024/{future_csv_name}")


# futures = read_czce_futures_txt('../data/CZCE/SAFUTURES2024.txt')
# futures.to_csv('../data/CZCE/SAFUTURES2024.csv')

# Sample data setup (replace with actual futures and PCR data)
# option_contract = 'SA411C1520'

for file in files_list:
    if file.endswith('2024.csv'):
        prefix = file.split("OPTIONS")[0]
        option = pd.read_csv(f"{folder_path}/ALLOPTIONS2024/{file}", parse_dates=True, index_col='交易日期')
        future_name = file.replace("OPTIONS", "FUTURES")
        future = pd.read_csv(f"{folder_path}/ALLFUTURES2024/{future_name}" , parse_dates=True, index_col='交易日期')
        future_df = future[future['合约代码'] == f"{prefix}412"]
        if future_df.empty:
            future_df = future[future['合约代码'] == f"{prefix}411"]
        option_df = option
        option_df['Option_Type'] = option_df['Delta'].apply(lambda x: 'Call' if x > 0 else 'Put')
        daily_volume = option_df.groupby([option_df.index, 'Option_Type'])['OpenInterest'].sum().unstack()
        daily_volume['PCR'] = daily_volume['Put'] / daily_volume['Call']
        pcr_df = daily_volume

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]})

        # Plot the K-line with volume on ax1 and PCR on ax2
        mpf.plot(future_df, type='candle', ax=ax1, volume=ax2, show_nontrading=True)

        # Adding PCR on a secondary y-axis aligned with ax1
        ax3 = ax1.twinx()
        ax3.plot(pcr_df.index, pcr_df['PCR'], color='blue', label='Put-Call Ratio (PCR)')
        ax3.set_ylabel('Put-Call Ratio (PCR)')
        ax3.legend(loc='upper left')

        plt.title(f"{prefix} Futures Price with Put-Call OpenInterest Ratio")
        plt.tight_layout()
        plt.savefig(f"../pictures/{prefix} OpenInterest.png", dpi=600)
        plt.show()



# future_contract = 'SA412'
# option = pd.read_csv("../data/CZCE/ALLOPTIONS2024/SAOPTIONS2024.csv", parse_dates=True, index_col='交易日期')
#
# future = pd.read_csv('../data/CZCE/ALLFUTURES2024/SAFUTURES2024.csv', parse_dates=True, index_col='交易日期')
# future_df = future[future['合约代码'] == future_contract]
#
# option_df = option[option['合约代码'].str.contains('SA')].copy()
#
# option_df['Option_Type'] = option_df['Delta'].apply(lambda x: 'Call' if x > 0 else 'Put')
# daily_volume = option_df.groupby([option_df.index,'Option_Type'])['OpenInterest'].sum().unstack()
# daily_volume['PCR'] = daily_volume['Put'] / daily_volume['Call']
# pcr_df = daily_volume
#
#
#
# # Plotting
# fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]})
#
# # Plot the K-line with volume on ax1 and PCR on ax2
# mpf.plot(future_df, type='candle', ax=ax1, volume=ax2, show_nontrading=True)
#
# # Adding PCR on a secondary y-axis aligned with ax1
# ax3 = ax1.twinx()
# ax3.plot(pcr_df.index, pcr_df['PCR'], color='blue', label='Put-Call Ratio (PCR)')
# ax3.set_ylabel('Put-Call Ratio (PCR)')
# ax3.legend(loc='upper left')
#
#
# # fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [3, 1, 1]})
# # mpf.plot(future_df, type='candle', ax=ax1, volume=ax2, show_nontrading=True)
# # ax3.plot(pcr_df.index, pcr_df['PCR'], label='Put/Call Ratio', color='purple')
# # ax3.set_ylabel("Put/Call Ratio")
# # ax3.set_xlabel("Date")
# # ax3.legend()
#
#
# plt.title("Futures Price with Put-Call Ratio")
# plt.tight_layout()
# plt.show()
