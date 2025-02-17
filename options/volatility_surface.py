import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# 如果你想要交互式的图像，可以使用 Plotly
import plotly.graph_objects as go


# 假设你的数据是以 pandas DataFrame 的形式存储
# 期权数据包含 'expiry', 'strike', 'implied_volatility'
contract_code = 'SA405'
option = pd.read_csv('../data/CZCE/ALLOPTIONS2024.csv')
option = option[(option["合约代码"].str.contains(contract_code))&(option['Delta']<0)]
# 将数据透视为到期时间 (expiry) 行权价格 (strike) 的二维表
pivot_table = option.pivot(index='合约代码', columns='交易日期', values='隐含波动率')

# 获取行权价格和到期时间
strikes = pivot_table.index.values
expiries = pivot_table.columns.values

# 获取隐含波动率
implied_vols = pivot_table.values
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

# 网格化数据
# X, Y = np.meshgrid(expiries, strikes)
# Z = implied_vols
#
# # 绘制曲面
# surf = ax.plot_surface(X, Y, Z, cmap='viridis')
#
# ax.set_xlabel('Expiry')
# ax.set_ylabel('Strike')
# ax.set_zlabel('Implied Volatility')
#
# plt.title('Implied Volatility Surface')
# plt.show()


fig = go.Figure(data=[go.Surface(z=implied_vols, x=expiries, y=strikes)])

fig.update_layout(title='Implied Volatility Surface',
                  scene = dict(
                      xaxis_title='Expiry',
                      yaxis_title='Strike',
                      zaxis_title='Implied Volatility'),
                  autosize=False,
                  width=800, height=800)

fig.show()

