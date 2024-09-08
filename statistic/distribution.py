import matplotlib.pyplot as plt
from utils.basic import read_data,transfer_period
import pandas as pd

dfdata = read_data('../data/SA/SA主力连续.csv')
dfday = transfer_period(dfdata, "D")
dfday['date'] = pd.to_datetime(dfday.index)
dfday['date'] = dfday['date'].apply(lambda x: x.strftime('%Y-%m-%d'))


# np.random.seed(0)
# price_data = np.random.normal(0, 1, 1000)  # 正态分布的价格数据，替换为实际数据
price_data = (dfday['Close']-dfday['Open'])/dfday['Close']*100
# 将价格数据放入Pandas数据框
df = pd.DataFrame({'Price': price_data})

# 计算价格百分比变动
df['Price_Pct_Change'] = df['Price']

# 删除第一行（NaN值）
df = df.dropna()

# 创建价格百分比变动的频率分布直方图
plt.hist(df['Price_Pct_Change'], bins=50, density=True, alpha=0.6, color='b', label='Price Percentage Change Histogram')

plt.xlabel('Price Percentage Change (%)')
plt.ylabel('Frequency')
plt.title('Futures Price Percentage Change Frequency Distribution')
plt.legend()
plt.show()