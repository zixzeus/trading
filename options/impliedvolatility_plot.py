import pandas as pd
import matplotlib.pyplot as plt

contract_name = "SA406C2000"

options_df = pd.read_csv("../data/CZCE/ALLOPTIONS2024.csv")
options_df["交易日期"] = pd.to_datetime(options_df["交易日期"])
options_df.set_index('交易日期', inplace=True)
options_df = options_df[options_df["合约代码"].str.contains(contract_name)]

plt.figure(figsize=(10, 6))
plt.plot(options_df["隐含波动率"], label="Implied Volatility", color="b")
plt.xlabel("Date")
plt.ylabel("Implied Volatility (%)")
plt.title("Implied Volatility Over Time")
plt.legend()
plt.grid(True)
plt.show()