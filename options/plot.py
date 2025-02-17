import pandas as pd
import mplfinance as mpf
from utils.basic import read_czce_options_txt

# 读取期权合约数据，假设数据包含日期、开盘价、最高价、最低价、收盘价
# 数据格式：Date, Open, High, Low, Close
option_contract = 'SA411C1520'
future_contract = 'SA405'

# option = read_czce_options_txt('../data/CZCE/ALLOPTIONS2024/SAOPTIONS2024.txt')


option = pd.read_csv("../data/CZCE/ALLOPTIONS2024/SAOPTIONS2024.csv", parse_dates=True, index_col='交易日期')
# option = pd.read_csv('../data/CZCE/ALLOPTIONS2024.csv', parse_dates=True, index_col='交易日期')
future = pd.read_csv('../data/CZCE/ALLFUTURES2024.csv', parse_dates=True, index_col='交易日期')

# future1['合约代码'] = future1['合约代码'].str.rstrip()

# future1.to_csv('../data/CZCE/ALLFUTURES2024.csv')

option1 = option[option['合约代码'] == option_contract]
option2 = option[option['合约代码'] == 'SA405C1600']
option3 = option[(option['合约代码'] == 'SA405C2000') | (option['合约代码'] == 'SA405P2000')]
future1 = future[future['合约代码'] == future_contract]
# 设置绘图参数
# apds = [mpf.make_addplot(option1['Close'], color='blue', panel=1),
#         mpf.make_addplot(option2['Close'], color='red', panel=2)
#         ]

# 绘制蜡烛图
mpf.plot(option1, type='candle', volume=True,
         title=f'Option Contract:{option_contract} Candle Stick Chart',
         style='yahoo', figsize=(10, 6))

# mpf.plot(future1, type='candle', volume=True,
#          title=f'Future Contract: {future_contract}',
#          style='yahoo', figsize=(10, 6))
