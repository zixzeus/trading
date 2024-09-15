import akshare as ak
from calculator import ImpliedVolatility, Calculator
import QuantLib as ql
import pandas as pd
import concurrent.futures


class OptionData:
    market_list = []
    target = None
    exchange_name = None

    def __init__(self, symbol, trade_date):
        self.symbol = symbol
        self.trade_date = trade_date
        self.part_1, self.part_2 = self.get_data()
        self.contract_code = None

    def get_data(self):
        pass

    def set_contract(self, code):
        self.contract_code = code

    def select_contract(self, contract_name):
        self.contract_code = contract_name
        sub_df = self.part_1[self.part_1["合约名称"].str.contains(contract_name)]
        return sub_df

    @staticmethod
    def select_at_the_money(df, option_type):
        if option_type == ql.Option.Call:
            if df['Delta'].empty:
                return None
            index = (df['Delta'] - 0.5).abs().argmin()
            at_the_money = df.iloc[index]
            return at_the_money
        elif option_type == ql.Option.Put:
            if df['Delta'].empty:
                return None
            index = (df['Delta'] + 0.5).abs().argmin()
            at_the_money = df.iloc[index]
            return at_the_money

    def add_pl_ratio(self):
        if self.contract_code is None:
            return None
        con_df = self.select_contract(self.contract_code).copy()
        if con_df.empty:
            return None
        con_df["pl_ratio"] = 0.0
        con_df["expected_return"] = 0.0
        con_df["kelly"] = 0.0

        call_df = self.select_option(con_df, option_type=ql.Option.Call)
        call_at_the_money = self.select_at_the_money(call_df, ql.Option.Call)
        call_at_the_price = float(call_at_the_money["收盘价"])
        for index, row in call_df.iterrows():
            close_price = row["收盘价"]
            try:
                pl_ratio = call_at_the_price / close_price
            except ZeroDivisionError:
                pl_ratio = 0
            con_df.loc[index, "pl_ratio"] = pl_ratio
            con_df.loc[index, "expected_return"] = row["Delta"] * pl_ratio
            if pl_ratio == 0:
                con_df.loc[index, "kelly"] =0
            else:
                con_df.loc[index, "kelly"] = row["Delta"] - (1 - row["Delta"]) / pl_ratio

        put_df = self.select_option(con_df, option_type=ql.Option.Put)
        put_at_the_money = self.select_at_the_money(put_df, ql.Option.Put)
        put_at_the_price = float(put_at_the_money["收盘价"])
        for index, row in put_df.iterrows():
            close_price = row["收盘价"]
            try:
                pl_ratio = put_at_the_price / close_price
            except ZeroDivisionError:
                pl_ratio = 0
            con_df.loc[index, "pl_ratio"] = pl_ratio
            con_df.loc[index, "expected_return"] = row["Delta"] * pl_ratio
            if pl_ratio == 0:
                con_df.loc[index, "kelly"] = 0
            else:
                con_df.loc[index, "kelly"] = row["Delta"] + (1 + row["Delta"]) / pl_ratio

        return con_df

    @staticmethod
    def select_option(df, option_type):
        if option_type == ql.Option.Call:
            sub_df = df[df["Delta"] > 0]
            return sub_df

        elif option_type == ql.Option.Put:
            sub_df = df[df["Delta"] < 0]
            return sub_df

    @classmethod
    def traversal(cls, trade_date):
        for option in cls.market_list:
            data = cls(symbol=option, trade_date=trade_date)
            for index, row in data.part_2.iterrows():
                option_name = row["合约系列"]
                data.set_contract(option_name)
                con_df = data.add_pl_ratio()
                if con_df is not None:
                    # con_df.to_excel(f"{option_name}-{trade_date}.xlsx", index=False)
                    selected_df = con_df[(con_df["expected_return"] < -1) | (con_df["expected_return"] > 1)]
                    cls.target = pd.concat([cls.target, selected_df], ignore_index=True)


class DCEOptionData(OptionData):
    market_list = ["玉米期权", "豆粕期权", "铁矿石期权", "液化石油气期权", "聚乙烯期权", "聚氯乙烯期权",
                   "聚丙烯期权", "棕榈油期权", "黄大豆1号期权", "黄大豆2号期权", "豆油期权", "乙二醇期权", "苯乙烯期权",
                   "鸡蛋期权", "玉米淀粉期权", "生猪期权"]
    exchange_name = "DCE"

    def get_data(self):
        self.part_1, self.part_2 = ak.option_dce_daily(self.symbol, self.trade_date)
        self.part_1["收盘价"] = pd.to_numeric(self.part_1["收盘价"].str.replace(',', ''))
        return self.part_1, self.part_2


class SHFEOptionData(OptionData):
    market_list = ["原油期权", "铜期权", "天胶期权", "丁二烯橡胶期权", "黄金期权", "白银期权", "铝期权", "锌期权",
                   "铅期权", "螺纹钢期权", "镍期权", "锡期权"]
    target = None
    exchange_name = "SHFE"

    def get_data(self):
        self.part_1, self.part_2 = ak.option_shfe_daily(self.symbol, self.trade_date)
        self.part_1.rename(columns={'合约代码': '合约名称', '德尔塔': 'Delta'}, inplace=True)
        self.part_2["合约系列"] = self.part_2["合约系列"].str.rstrip()
        self.part_2 = self.part_2.drop(self.part_2.index[-1])
        return self.part_1, self.part_2


class CZCEOptionData(OptionData):
    market_list = ["白糖期权", "棉花期权", "甲醇期权", "PTA期权", "菜籽粕期权", "动力煤期权", "短纤期权",
                   "菜籽油期权", "花生期权", "短纤期权", "纯碱期权", "锰硅期权", "硅铁期权", "尿素期权",
                   "对二甲苯期权",
                   "烧碱期权", "玻璃期权"]
    target = None
    exchange_name = "CZCE"

    def get_data(self):
        self.part_1 = ak.option_czce_daily(symbol=self.symbol, trade_date=self.trade_date)
        self.part_1.columns = [col.rstrip() for col in self.part_1.columns]
        self.part_1.rename(columns={'合约代码': '合约名称', '今收盘': '收盘价', 'DELTA': 'Delta'}, inplace=True)
        self.part_1["Delta"] = pd.to_numeric(self.part_1["Delta"])
        self.part_1["收盘价"] = pd.to_numeric(self.part_1["收盘价"].str.replace(',', ''))
        self.part_2 = pd.DataFrame()
        self.part_2["合约系列"] = self.part_1['合约名称'].str.extract(r'([A-Z]+\d+)').drop_duplicates().reset_index(
            drop=True)
        return self.part_1, self.part_2


class GFEXOptionData(OptionData):
    market_list = ["工业硅", "碳酸锂"]
    target = None
    exchange_name = "GFEX"

    def get_data(self):
        self.part_1 = ak.option_gfex_daily(symbol=self.symbol, trade_date=self.trade_date)
        self.part_2 = ak.option_gfex_vol_daily(symbol=self.symbol, trade_date=self.trade_date)

        return self.part_1, self.part_2


# 模拟从不同交易所获取期权数据的函数
def fetch_data_from_exchange(exchange,trade_date):
    print(f"Fetching data from {exchange.exchange_name}...")

    exchange.traversal(trade_date=trade_date)
    # 模拟数据获取延迟
    return exchange.target,exchange.exchange_name


# 获取三个交易所的数据
def fetch_all_data():
    exchanges = [SHFEOptionData, CZCEOptionData, DCEOptionData, GFEXOptionData]
    trade_dates = ["20240913","20240913","20240913","20240913"]
    # 使用 ThreadPoolExecutor 进行多线程
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # 提交所有的任务并获取结果
        results = executor.map(fetch_data_from_exchange, exchanges,trade_dates)

    for result in results:
        print(result[0])
        result[0].to_excel(f"../data/{result[1]}_{trade_dates[0]}.xlsx")


if __name__ == "__main__":
    fetch_all_data()
    # CZCEOptionData.traversal(trade_date="20240910")
    # print(CZCEOptionData.target)
    # CZCEOptionData.target.to_excel("../data/CZCE_target.xlsx", index=False)

    # SHFEOptionData.traversal(trade_date="20240910")
    # print(SHFEOptionData.target)
    # SHFEOptionData.target.to_excel("../data/SHFE_Shit_target.xlsx", index=False)

    # DCEOptionData.traversal(trade_date="20240911")
    # print(DCEOptionData.target)
    # DCEOptionData.target.to_excel("../data/DCE_target1.xlsx", index=False)

    # GFEXOptionData.traversal(trade_date="20240910")
    # print(GFEXOptionData.target)
    # GFEXOptionData.target.to_excel("../data/GFEX_target.xlsx", index=False)


# option_commodity_contract_table_sina_df = ak.option_commodity_contract_table_sina(symbol="豆粕期权", contract="m2501")
# print(option_commodity_contract_table_sina_df)


# print("看涨合约买量求和")
# print(option_commodity_contract_table_sina_df["看涨合约-买量"].sum())


# option_commodity_hist_sina_df = ak.option_commodity_hist_sina(symbol="m2411C3350")
# print(option_commodity_hist_sina_df)
