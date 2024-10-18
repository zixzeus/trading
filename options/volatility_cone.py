import numpy as np
import matplotlib.pyplot as plt
from utils.basic import read_data, transfer_period
import pandas as pd

dfdata = read_data('../data/SA/SA主力连续.csv')
dfday = transfer_period(dfdata, "D")
dfday['date'] = pd.to_datetime(dfday.index)
dfday['date'] = dfday['date'].apply(lambda x: x.strftime('%Y-%m-%d'))
price_data = dfday


# 3. 定义一个计算年化波动率的函数
def calc_rolling_volatility(price_series, window):
    log_returns = np.log(price_series / price_series.shift(1))
    rolling_volatility = log_returns.rolling(window=window).std() * np.sqrt(252)  # 年化波动率
    return rolling_volatility


# 4. 计算不同时间窗口的波动率（30天、60天、90天、120天）
vol_30 = calc_rolling_volatility(price_data['Close'], 30)
vol_60 = calc_rolling_volatility(price_data['Close'], 60)
vol_90 = calc_rolling_volatility(price_data['Close'], 90)
vol_120 = calc_rolling_volatility(price_data['Close'], 120)
vol_150 = calc_rolling_volatility(price_data['Close'], 150)
vol_180 = calc_rolling_volatility(price_data['Close'], 180)
vol_210 = calc_rolling_volatility(price_data['Close'], 210)

# 5. 将不同窗口的波动率汇集到一个DataFrame中
vol_data = pd.DataFrame({
    '30-Day': vol_30,
    '60-Day': vol_60,
    '90-Day': vol_90,
    '120-Day': vol_120,
    '150-Day': vol_150,
    '180-Day': vol_180,
    '210-Day': vol_210
})

# 6. 计算百分位数
percentiles = {
    'Min': vol_data.min(),
    '5%': vol_data.quantile(0.05),
    '25%': vol_data.quantile(0.25),
    '50% (Median)': vol_data.quantile(0.50),
    '75%': vol_data.quantile(0.75),
    '95%': vol_data.quantile(0.95),
    'Max': vol_data.max()
}

# 7. 绘制波动率锥
plt.figure(figsize=(10, 6))

# 绘制不同窗口的百分位数
plt.plot([30, 60, 90, 120, 150, 180, 210], percentiles['Min'], label='Min', color='yellow', linestyle='--')
plt.plot([30, 60, 90, 120, 150, 180, 210], percentiles['5%'], label='5th Percentile', color='blue', linestyle='--')
plt.plot([30, 60, 90, 120, 150, 180, 210], percentiles['25%'], label='25th Percentile', color='blue', linestyle='--')
plt.plot([30, 60, 90, 120, 150, 180, 210], percentiles['50% (Median)'], label='50th Percentile (Median)', color='green',
         linestyle='-')
plt.plot([30, 60, 90, 120, 150, 180, 210], percentiles['75%'], label='75th Percentile', color='red', linestyle='--')
plt.plot([30, 60, 90, 120, 150, 180, 210], percentiles['95%'], label='95th Percentile', color='red', linestyle='--')
plt.plot([30, 60, 90, 120, 150, 180, 210], percentiles['Max'], label='Max', color='black', linestyle='--')
# 填充区域
plt.fill_between([30, 60, 90, 120, 150, 180, 210], percentiles['25%'], percentiles['75%'], color='gray', alpha=0.1)
plt.fill_between([30, 60, 90, 120, 150, 180, 210], percentiles['25%'], percentiles['Min'], color='gray', alpha=0.2)
plt.fill_between([30, 60, 90, 120, 150, 180, 210], percentiles['75%'], percentiles['Max'], color='gray', alpha=0.2)
# 图表细节
plt.title('Volatility Cone')
plt.xlabel('Time Window (Days)')
plt.ylabel('Annualized Volatility')
plt.xticks([30, 60, 90, 120, 150, 180, 210])
plt.legend()
plt.grid(True)

# 显示图表
plt.show()
