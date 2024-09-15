import akshare as ak
import pandas as pd
from calculator import VolCalculator,ImVolCalculator
# option_czce_hist_df = ak.option_czce_hist(symbol="ZC", year="2021")

# for date in ["20240909", "20240910", "20240911", "20240912", "20240913"]:
#     part1, part2 = ak.option_shfe_daily("锌期权", date)
#     print(part1)
#     print(part2)
# print(option_czce_hist_df)

sh_df = pd.read_excel("../data/MarketData_Year_2024/所内合约行情报表2024.1.xls",skiprows=3,skipfooter=5)
sh_df.drop(sh_df.columns[-1], axis=1, inplace=True)
sh_df['Contract'] = sh_df['Contract'].fillna(method='ffill')
print(sh_df)


option_commodity_hist_sina_df = ak.option_commodity_hist_sina(symbol="zn2410C24000")
print(option_commodity_hist_sina_df)
