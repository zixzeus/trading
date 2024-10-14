import akshare as ak
import pandas as pd
from calculator import VolCalculator, ImVolCalculator
import QuantLib as ql
from datetime import datetime
import mplfinance as mpf
import matplotlib.pyplot as plt
import timeit


def get_option_expiry(year: int, month: int) -> pd.Timestamp:
    # 获取当年的所有交易日历
    trade_days = ak.tool_trade_date_hist_sina()

    if month == 1:
        month = 12
        year = year - 1
    else:
        month = month - 1
        year = year
    # 过滤出目标月份的交易日
    trade_days['date'] = pd.to_datetime(trade_days['trade_date'])
    monthly_trade_days = trade_days[(trade_days['date'].dt.year == year) & (trade_days['date'].dt.month == month)]

    # 倒数第四个交易日
    if monthly_trade_days.empty:
        workdays = pd.bdate_range(start=f"{year}-{month}", end=f"{year}-{month + 1}")
        expiry_date = workdays[-5]
    else:
        expiry_date = monthly_trade_days.iloc[-5]['date']
    return expiry_date


class SHFEHistOptionAnalysis:

    def __init__(self, file_path):
        self._file_path = file_path
        self.data = pd.DataFrame()

    @property
    def file_path(self):
        return self._file_path

    @file_path.setter
    def file_path(self, file_path):
        self._file_path = file_path

    def load_data(self):
        self.data = pd.read_excel(self.file_path, skiprows=3, skipfooter=5)
        self.data.drop(self.data.columns[-1], axis=1, inplace=True)
        self.data['Contract'] = self.data['Contract'].ffill()
        self.data["Delta"] = 0.0
        self.data["pl_ratio"] = 0.0
        self.data["expected_return"] = 0.0
        self.data["kelly"] = 0.0
        self.data["strike_price"] = 0.0
        self.data["option_type"] = ""
        return self

    @staticmethod
    def iterate_daterange(date_range, func_date, *args, **kwargs):
        for date in date_range:
            func_date(date, *args, **kwargs)

    def get_future_contracts(self):
        contracts = pd.DataFrame()
        contracts["Contract"] = self.data['Contract'].str.extract(r'([a-z]+\d+)').drop_duplicates().reset_index(
            drop=True)
        return contracts

    def select_future_contract(self, future_contract):
        future_df = self.data[self.data['Contract'] == future_contract]
        return future_df

    def select_option_contract(self, future_contract):
        option_df = self.data[self.data["Contract"].str.contains(f"^{future_contract}(?!$)", regex=True)]
        return option_df

    @staticmethod
    def select_day_option_contract(option_df, date):
        day_df = option_df.loc[option_df['Date'] == date]
        return day_df

    def add_greek(self, future_contract):
        future_df = self.select_future_contract(future_contract)
        future_df.set_index("Date", inplace=True)
        # option_df = self.select_option_contract(future_contract).reset_index(drop=True)
        option_df = self.select_option_contract(future_contract).copy()
        option_df["strike_price"] = option_df["Contract"].str.extract(r'(\d+)$')
        option_df["strike_price"] = pd.to_numeric(option_df["strike_price"])
        option_df["option_type"] = option_df["Contract"].str.extract(r'([A-Z])(?=\d)')

        digit = future_contract[-4:]
        year = int('20' + digit[:2])
        month = int(digit[2:])
        ex_date = get_option_expiry(year, month)
        expiration_date = ql.Date(ex_date.day, ex_date.month, ex_date.year)
        Iv = ImVolCalculator()
        Iv.expiration_date = expiration_date
        self.iterate_daterange(future_df.index, self.process_day_option, future_df, option_df, ImVolCalculator=Iv)
        return option_df

    def process_day_option(self, date, *args, **kwargs):
        future_df = args[0]
        option_df = args[1]
        Iv = kwargs['ImVolCalculator']
        day_df = self.select_day_option_contract(option_df, date)
        if day_df.empty:
            return
        current_price = future_df.loc[date]["Close"]
        date_obj = datetime.strptime(str(date), "%Y%m%d")
        call_df = day_df[day_df["option_type"] == "C"]
        index0 = (call_df["strike_price"] - current_price).abs().argmin()
        call_at_the_money = call_df.iloc[index0]
        put_df = day_df[day_df["option_type"] == "P"]
        index1 = (put_df["strike_price"] - current_price).abs().argmin()
        put_at_the_money = put_df.iloc[index1]
        for index, row in day_df.iterrows():
            option_price = row["Close"]
            strike_price = row["strike_price"]
            if row["option_type"] == "C":
                option_type = ql.Option.Call
                option_df.loc[index, "pl_ratio"] = call_at_the_money["Close"] / row["Close"]

            else:
                option_type = ql.Option.Put
                option_df.loc[index, "pl_ratio"] = put_at_the_money["Close"] / row["Close"]

            Iv.option_price = option_price
            Iv.strike_price = strike_price
            # Iv.expiration_date = expiration_date
            Iv.current_price = current_price
            Iv.evaluation_date = ql.Date(date_obj.day, date_obj.month, date_obj.year)
            Iv.option_type = option_type
            Iv.load_bs_model()
            Iv.get_greek()
            Iv.check_initialized()
            day_df.loc[index, "Delta"] = Iv.greek.get("Delta")
            option_df.loc[index, "Delta"] = Iv.greek.get("Delta")
            option_df.loc[index, "expected_return"] = option_df.loc[index, "Delta"] * option_df.loc[index, "pl_ratio"]

            if row["option_type"] == "C":
                if option_df.loc[index, "pl_ratio"] == 0:
                    option_df.loc[index, "kelly"] = 0
                else:
                    option_df.loc[index, "kelly"] = option_df.loc[index, "Delta"] - (
                            1 - option_df.loc[index, "Delta"]) / option_df.loc[index, "pl_ratio"]
            else:
                if option_df.loc[index, "pl_ratio"] == 0:
                    option_df.loc[index, "kelly"] = 0
                else:
                    option_df.loc[index, "kelly"] = option_df.loc[index, "Delta"] + (
                            1 + option_df.loc[index, "Delta"]) / option_df.loc[index, "pl_ratio"]

    def update_all_contracts(self):
        future_contracts = self.get_future_contracts()
        for index, future_contract in future_contracts.iterrows():
            option_df = self.add_greek(future_contract['Contract'])
            # print(option_df)
            if not option_df.empty:
                self.data.update(option_df)

    def plot(self, option_df):
        option_df.dropna(subset=['Open', 'High', 'Low', 'Close'], inplace=True)
        option_df['Date'] = pd.to_datetime(option_df['Date'], format='%Y%m%d')
        option_df.set_index('Date', inplace=True)
        option_df.sort_index(inplace=True)
        # ag_option_df = option_df[option_df['Contract'] == 'ag2406C6500']
        # future_df.index = pd.to_datetime(future_df.index, format='%Y%m%d')
        mpf.plot(option_df, type='candle', style='charles', volume=True, title='Options Historical K-Line Chart')
        plt.show()


def calculate_profit_ratio(row, atm_call_price, atm_put_price):
    if row['option_type'] == 'C':
        return row['Close'] / atm_call_price if atm_call_price > 0 else None
    elif row['option_type'] == 'P':
        return row['Close'] / atm_put_price if atm_put_price > 0 else None


# 示例：获取2024年9月的期权合约到期日
# option_commodity_hist_sina_df = ak.option_commodity_hist_sina(symbol="zn2410C24000")
# print(option_commodity_hist_sina_df)

if __name__ == "__main__":
    # def a():
    #     file = "../data/MarketData_Year_2024/所内合约行情报表2024.3.xls"
    #     SA = SHFEHistOptionAnalysis(file).load_data()
    #     SA.update_all_contracts()
    #     # option_df = SA.add_greek("ag2406")
    #     # ag_option_df = option_df[option_df['Contract'] == 'ag2406C6300'].copy()
    #     # SA.plot(ag_option_df)
    #     print(SA.data)
    #     SA.data.to_excel("../data/MarketData_Year_2024/market_date_test.3.xlsx")

    option_df = pd.read_table('../data/CZCE/ALLOPTIONS2023.txt', skiprows=1, sep="|", low_memory=False)
    print(option_df)
    # execution_time = timeit.timeit("a()", globals=locals(), number=1)
    # print("Execution Time: ", execution_time)
    # expiry_date = get_option_expiry(2024, 11)
    #
    option_czce_hist_df = ak.option_czce_hist(symbol="SA", year="2023")
    # print(option_czce_hist_df)
    # print(f"2024年9月的期权到期日为: {expiry_date}")
