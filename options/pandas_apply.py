import pandas as pd

# df = pd.read_excel("../data/SHFE_20240918.xlsx")

# df.apply(pd.to_numeric, errors='coerce')
# print(df)


# 示例数据框
data = {
    'type': ['Call', 'Call', 'Put', 'Put', 'Call'],
    'strike': [100, 105, 100, 95, 110],
    'price': [10, 8, 7, 5, 6],
    'underlying_price': [102, 102, 102, 102, 102]  # 假设标的资产价格固定
}
df = pd.DataFrame(data)


# 定义计算盈亏比的函数
def calculate_profit_ratio(row, atm_call_price, atm_put_price):
    if row['type'] == 'Call':
        return row['price'] / atm_call_price if atm_call_price > 0 else None
    elif row['type'] == 'Put':
        return row['price'] / atm_put_price if atm_put_price > 0 else None


# 找到平值期权
atm_strike = df['underlying_price'].iloc[0]
atm_call_price = 100
atm_put_price = 110

# 使用 apply 函数计算盈亏比
df['profit_ratio'] = df.apply(calculate_profit_ratio, axis=1, args=(atm_call_price, atm_put_price))

print(df)
