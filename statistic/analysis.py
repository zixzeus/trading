import matplotlib.pyplot as plt
import pandas as pd

filepath = "../data/macro.csv"
df = pd.read_csv(filepath)

# 打印相关性矩阵

# 获取特定两列的相关性值
df["Date"] = pd.to_datetime(df["Date"])

df = df.resample("M",on="Date").mean().dropna()
keys = ["Interest","USIndex","Silver","Dow","NFP","CPI","CO"]

a=keys[6]
b=keys[2]
for _ in keys:
    correlation_value = df[_].corr(df[b])
    print(f"Correlation between {_} and {b}: {correlation_value}")
# print(df)

if __name__ == '__main__':
    ""
