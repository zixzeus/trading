import akshare as ak
from calculator import ImpliedVolatility, Calculator
import QuantLib as ql
import pandas as pd


class OptionData:
    market_list = []
    target = None

    def __init__(self, symbol, trade_date):
        self.symbol = symbol
        self.trade_date = trade_date
        self.part_1, self.part_2 = self.get_data()
        self.contract_code = None

    def get_data(self):
        """获取期权数据的基类方法，子类会覆盖这个方法。"""
        pass

    def set_contract(self, code):
        """设置当前操作的合约代码。"""
        self.contract_code = code

    def select_contract(self, contract_name):
        """根据合约名称筛选期权数据。"""
        self.contract_code = contract_name
        sub_df = self.part_1[self.part_1["合约名称"].str.contains(contract_name)]
        return sub_df

    @staticmethod
    def select_at_the_money(df, option_type):
        """选择平值期权，使用Delta值接近0.5的期权。"""
        if df['Delta'].empty:
            return None
        delta_target = 0.5 if option_type == ql.Option.Call else -0.5
        index = (df['Delta'] - delta_target).abs().argmin()
        return df.iloc[index]

    def calculate_ratios(self, df, at_the_money_price):
        """计算盈亏比率和预期收益，并更新到DataFrame中。"""
        df["pl_ratio"] = 0.0
        df["expected_return"] = 0.0

        for index, row in df.iterrows():
            close_price = self.get_close_price(row["收盘价"])
            pl_ratio = self.safe_divide(at_the_money_price, close_price)
            df.loc[index, "pl_ratio"] = pl_ratio
            df.loc[index, "expected_return"] = row["Delta"] * pl_ratio

    def add_pl_ratio(self):
        """计算并返回包含盈亏比率和预期收益的DataFrame。"""
        if not self.contract_code:
            return None

        con_df = self.select_contract(self.contract_code).copy()
        if con_df.empty:
            return None

        # 处理看涨期权
        call_df = self.select_option(con_df, option_type=ql.Option.Call)
        call_at_the_money = self.select_at_the_money(call_df, ql.Option.Call)
        if call_at_the_money is not None:
            self.calculate_ratios(call_df, float(call_at_the_money["收盘价"]))

        # 处理看跌期权
        put_df = self.select_option(con_df, option_type=ql.Option.Put)
        put_at_the_money = self.select_at_the_money(put_df, ql.Option.Put)
        if put_at_the_money is not None:
            self.calculate_ratios(put_df, float(put_at_the_money["收盘价"]))

        return con_df

    @staticmethod
    def get_close_price(price):
        """处理收盘价的数据类型并转换为浮点数。"""
        if isinstance(price, str):
            return float(price.replace(',', ''))
        elif isinstance(price, (int, float)):
            return price
        return 0

    @staticmethod
    def safe_divide(a, b):
        """安全的除法操作，避免除以0。"""
        try:
            return a / b
        except ZeroDivisionError:
            return 0

    @staticmethod
    def select_option(df, option_type):
        """根据期权类型筛选看涨或看跌期权。子类需要实现这个方法。"""
        pass

    @classmethod
    def traversal(cls, trade_date):
        """遍历市场列表中的期权数据，并保存筛选后的结果到Excel文件中。"""
        count = 0
        for option in cls.market_list:
            data = cls(symbol=option, trade_date=trade_date)
            for index, row in data.part_2.iterrows():
                option_name = row["合约系列"]
                data.set_contract(option_name)
                con_df = data.add_pl_ratio()

                if con_df is not None:
                    # 保存到Excel
                    con_df.to_excel(f"{option_name}-{trade_date}.xlsx", index=False)

                    # 更新目标数据
                    selected_df = con_df[(con_df["expected_return"] < -1) | (con_df["expected_return"] > 1)]
                    cls.target = pd.concat([cls.target, selected_df], ignore_index=True) if count >= 1 else selected_df
                    count += 1


class DCEOptionData(OptionData):
    market_list = [
        "玉米期权", "豆粕期权", "铁矿石期权", "液化石油气期权", "聚乙烯期权", "聚氯乙烯期权",
        "聚丙烯期权", "棕榈油期权", "黄大豆1号期权", "黄大豆2号期权", "豆油期权", "乙二醇期权",
        "苯乙烯期权", "鸡蛋期权", "玉米淀粉期权", "生猪期权"
    ]

    def get_data(self):
        """获取大连商品期权数据。"""
        return ak.option_dce_daily(self.symbol, self.trade_date)

    @staticmethod
    def select_option(df, option_type):
        """筛选看涨期权或看跌期权。"""
        return df[df["合约名称"].str.contains("-C-" if option_type == ql.Option.Call else "-P-")]


class SHFEOptionData(OptionData):
    market_list = [
        "原油期权", "铜期权", "天胶期权", "丁二烯橡胶期权", "黄金期权", "白银期权", "铝期权",
        "锌期权", "铅期权", "螺纹钢期权", "镍期权", "锡期权"
    ]

    def get_data(self):
        """获取上海期货交易所期权数据，并清理数据格式。"""
        self.part_1, self.part_2 = ak.option_shfe_daily(self.symbol, self.trade_date)
        self.part_1.rename(columns={'合约代码': '合约名称', '德尔塔': 'Delta'}, inplace=True)
        self.part_2["合约系列"] = self.part_2["合约系列"].str.rstrip()
        self.part_2 = self.part_2.drop(self.part_2.index[-1])  # 移除最后一行（可能是无效数据）
        return self.part_1, self.part_2

    @staticmethod
    def select_option(df, option_type):
        """筛选看涨期权或看跌期权。"""
        return df[df["合约名称"].str.contains("C" if option_type == ql.Option.Call else "P")]


class CZCEOptionData(OptionData):
    market_list = [
        "白糖期权", "棉花期权", "甲醇期权", "PTA期权", "菜籽粕期权", "动力煤期权", "短纤期权",
        "菜籽油期权", "花生期权", "棉花期权", "短纤期权", "纯碱期权", "锰硅期权", "硅铁期权",
        "尿素期权", "对二甲苯期权", "烧碱期权", "玻璃期权"
    ]

    def get_data(self):
        """获取郑州商品期权数据，并处理数据格式。"""
        self.part_1 = ak.option_czce_daily(symbol=self.symbol, trade_date=self.trade_date)
        self.part_1.columns = [col.rstrip() for col in self.part_1.columns]  # 去除列名中的空格
        self.part_1.rename(columns={'合约代码': '合约名称', '今收盘': '收盘价', 'DELTA': 'Delta'}, inplace=True)
        self.part_1["Delta"] = pd.to_numeric(self.part_1["Delta"], errors='coerce')  # 转换为数值型
        self.part_2 = pd.DataFrame()
        self.part_2["合约系列"] = self.part_1['合约名称'].str.extract(r'([A-Z]+\d+)').drop_duplicates().reset_index(drop=True)
        return self.part_1, self.part_2

    @staticmethod
    def select_option(df, option_type):
        """筛选看涨期权或看跌期权。"""
        return df[df["合约名称"].str.contains("C" if option_type == ql.Option.Call else "P")]


CZCEOptionData.traversal(trade_date="20240910")
print(CZCEOptionData.target)
CZCEOptionData.target.to_excel("CZCE_target2.xlsx", index=False)