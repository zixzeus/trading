import akshare as ak
try:
    from calculator import VolCalculator, ImVolCalculator
except ImportError:
    from options.calculator import VolCalculator, ImVolCalculator
import QuantLib as ql
import pandas as pd
import concurrent.futures
import os

class OptionData:
    market_list = []
    target = None
    exchange_name = None

    def __init__(self, symbol, trade_date):
        self._symbol = symbol
        self._trade_date = trade_date
        self._part_1, self._part_2 = self.get_data()
        self._contract_code = None

    @property
    def symbol(self):
        return self._symbol

    @symbol.setter
    def symbol(self, symbol):
        self._symbol = symbol

    @property
    def trade_date(self):
        return self._trade_date

    @trade_date.setter
    def trade_date(self, trade_date):
        self._trade_date = trade_date

    @property
    def contract_code(self):
        return self._contract_code

    @contract_code.setter
    def contract_code(self, contract_code):
        self._contract_code = contract_code

    def get_data(self):
        pass

    def select_contract(self, contract_name):
        self.contract_code = contract_name
        sub_df = self.part_1[self.part_1["合约名称"].str.contains(contract_name)]
        return sub_df

    @staticmethod
    def select_at_the_money(df, option_type):
        if option_type == ql.Option.Call:
            # 过滤掉NaN值
            valid_df = df[df['Delta'].notna()]
            if valid_df.empty:
                return None
            # 使用loc来确保正确的索引对应
            idx = (valid_df['Delta'] - 0.5).abs().idxmin()
            at_the_money = valid_df.loc[idx]
            return at_the_money
        elif option_type == ql.Option.Put:
            # 过滤掉NaN值
            valid_df = df[df['Delta'].notna()]
            if valid_df.empty:
                return None
            # 使用loc来确保正确的索引对应
            idx = (valid_df['Delta'] + 0.5).abs().idxmin()
            at_the_money = valid_df.loc[idx]
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
        if not call_df.empty:
            call_at_the_money = self.select_at_the_money(call_df, ql.Option.Call)
            if call_at_the_money is not None:
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
                        con_df.loc[index, "kelly"] = 0
                    else:
                        con_df.loc[index, "kelly"] = row["Delta"] - (1 - row["Delta"]) / pl_ratio

        put_df = self.select_option(con_df, option_type=ql.Option.Put)
        if not put_df.empty:
            put_at_the_money = self.select_at_the_money(put_df, ql.Option.Put)
            if put_at_the_money is not None:
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
            # 过滤掉NaN值，只选择Delta > 0的行
            sub_df = df[(df["Delta"].notna()) & (df["Delta"] > 0)]
            return sub_df

        elif option_type == ql.Option.Put:
            # 过滤掉NaN值，只选择Delta < 0的行
            sub_df = df[(df["Delta"].notna()) & (df["Delta"] < 0)]
            return sub_df

    @classmethod
    def traversal(cls, trade_date):
        # Initialize target as empty DataFrame if it's None
        if cls.target is None:
            cls.target = pd.DataFrame()
            
        for option in cls.market_list:
            try:
                data = cls(symbol=option, trade_date=trade_date)
                
                # 检查数据是否为空
                if data.part_1.empty or data.part_2.empty:
                    print(f"警告: {option} 在 {trade_date} 没有数据")
                    continue
                    
                for index, row in data.part_2.iterrows():
                    option_name = row["合约系列"]
                    data.contract_code = option_name
                    con_df = data.add_pl_ratio()
                    if con_df is not None and not con_df.empty:
                        # con_df.to_excel(f"{option_name}-{trade_date}.xlsx", index=False)
                        selected_df = con_df[(con_df["expected_return"] < -1) | (con_df["expected_return"] > 1)]
                        if not selected_df.empty:
                            cls.target = pd.concat([cls.target, selected_df], ignore_index=True)
            except Exception as e:
                print(f"处理 {option} 时出错: {e}")
                continue


class DCEOptionData(OptionData):
    market_list = ["玉米期权", "豆粕期权", "铁矿石期权", "液化石油气期权", "聚乙烯期权", "聚氯乙烯期权",
    "聚丙烯期权", "棕榈油期权", "黄大豆1号期权", "黄大豆2号期权", "豆油期权", "乙二醇期权", "苯乙烯期权",
    "鸡蛋期权", "玉米淀粉期权", "生猪期权", "原木期权"]
    exchange_name = "DCE"

    def get_data(self):
        self.part_1, self.part_2 = ak.option_dce_daily(self.symbol, self.trade_date)
        
        # 检查是否获取到数据
        if self.part_1.empty:
            return self.part_1, self.part_2
            
        # 处理收盘价列
        if '收盘价' in self.part_1.columns:
            self.part_1["收盘价"] = pd.to_numeric(self.part_1["收盘价"].str.replace(',', ''), errors='coerce')
        
        # 处理Delta列，将'-'转换为NaN，然后转换为数值类型
        if 'Delta' in self.part_1.columns:
            self.part_1["Delta"] = pd.to_numeric(self.part_1["Delta"].replace('-', pd.NA), errors='coerce')
        return self.part_1, self.part_2


class SHFEOptionData(OptionData):
    market_list = ["原油期权", "铜期权", "天胶期权", "丁二烯橡胶期权", "黄金期权", "白银期权", "铝期权", "锌期权",
                   "铅期权", "螺纹钢期权", "镍期权", "锡期权", "铸造铝合金期权","氧化铝期权"]
    target = None
    exchange_name = "SHFE"

    def get_data(self):
        self.part_1, self.part_2 = ak.option_shfe_daily(self.symbol, self.trade_date)
        
        # 检查是否获取到数据
        if self.part_1.empty:
            return self.part_1, self.part_2
            
        self.part_1.rename(columns={'合约代码': '合约名称', '德尔塔': 'Delta'}, inplace=True)
        
        # 处理Delta列，将'-'转换为NaN，然后转换为数值类型
        if 'Delta' in self.part_1.columns:
            self.part_1["Delta"] = pd.to_numeric(self.part_1["Delta"].replace('-', pd.NA), errors='coerce')
        
        if not self.part_2.empty and '合约系列' in self.part_2.columns:
            self.part_2["合约系列"] = self.part_2["合约系列"].str.rstrip()
            self.part_2 = self.part_2.drop(self.part_2.index[-1])
        return self.part_1, self.part_2


class CZCEOptionData(OptionData):
    market_list = ["白糖期权", "棉花期权", "甲醇期权", "PTA期权", "动力煤期权", "菜籽粕期权", "菜籽油期权",
    "花生期权", "对二甲苯期权", "烧碱期权", "纯碱期权", "短纤期权", "锰硅期权", "硅铁期权", "尿素期权", "苹果期权", "红枣期权",
    "玻璃期权", "瓶片期权"]
    target = None
    exchange_name = "CZCE"

    def get_data(self):
        self.part_1 = ak.option_czce_daily(symbol=self.symbol, trade_date=self.trade_date)
        
        # 检查是否获取到数据
        if self.part_1.empty:
            self.part_2 = pd.DataFrame()
            return self.part_1, self.part_2
            
        self.part_1.columns = [col.rstrip() for col in self.part_1.columns]
        self.part_1.rename(columns={'合约代码': '合约名称', '今收盘': '收盘价', 'DELTA': 'Delta'}, inplace=True)
        
        # 处理Delta列，将'-'转换为NaN，然后转换为数值类型
        if 'Delta' in self.part_1.columns:
            self.part_1["Delta"] = pd.to_numeric(self.part_1["Delta"].replace('-', pd.NA), errors='coerce')
        
        # 处理收盘价列
        if '收盘价' in self.part_1.columns:
            self.part_1["收盘价"] = pd.to_numeric(self.part_1["收盘价"].replace(',', ''), errors='coerce')
        
        self.part_2 = pd.DataFrame()
        if '合约名称' in self.part_1.columns:
            self.part_2["合约系列"] = self.part_1['合约名称'].str.extract(r'([A-Z]+\d+)').drop_duplicates().reset_index(
                drop=True)
        return self.part_1, self.part_2


class GFEXOptionData(OptionData):
    market_list = ["工业硅", "碳酸锂","多晶硅"]
    target = None
    exchange_name = "GFEX"

    def get_data(self):
        self.part_1 = ak.option_gfex_daily(symbol=self.symbol, trade_date=self.trade_date)
        self.part_2 = ak.option_gfex_vol_daily(symbol=self.symbol, trade_date=self.trade_date)
        
        # 检查是否获取到数据
        if self.part_1 is None:
            self.part_1 = pd.DataFrame()
        if self.part_2 is None:
            self.part_2 = pd.DataFrame()
            
        # 处理Delta列，将'-'转换为NaN，然后转换为数值类型
        if not self.part_1.empty and 'Delta' in self.part_1.columns:
            self.part_1["Delta"] = pd.to_numeric(self.part_1["Delta"].replace('-', pd.NA), errors='coerce')
        return self.part_1, self.part_2


# 模拟从不同交易所获取期权数据的函数
def fetch_data_from_exchange(exchange, trade_date):
    print(f"Fetching data from {exchange.exchange_name}...")

    exchange.traversal(trade_date=trade_date)
    # 模拟数据获取延迟
    return exchange.target, exchange.exchange_name


# 获取三个交易所的数据
def fetch_all_data():
    exchanges = [SHFEOptionData, CZCEOptionData, DCEOptionData, GFEXOptionData]
    trade_dates = ["20250801" for _ in range(4)]
    
    # 使用绝对路径

    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    
    # 确保数据目录存在
    os.makedirs(data_dir, exist_ok=True)
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(fetch_data_from_exchange, exchanges, trade_dates)

    for result in results:
        print(result[0])
        output_path = os.path.join(data_dir, f"{result[1]}_{trade_dates[0]}.xlsx")
        
        # Check if result[0] is not None and not empty before saving
        if result[0] is not None and not result[0].empty:
            result[0].to_excel(output_path)
            print(f"数据已保存到: {output_path}")
        else:
            print(f"警告: {result[1]} 没有符合条件的数据，跳过保存")


if __name__ == "__main__":
    fetch_all_data()
    # trade_date = "20241015"
    # CZCEOptionData.traversal(trade_date=trade_date)
    # print(CZCEOptionData.target)
    # CZCEOptionData.target.to_excel(f"../data/CZCE_{trade_date}.xlsx", index=False)

    # SHFEOptionData.traversal(trade_date="20241008")
    # print(SHFEOptionData.target)
    # SHFEOptionData.target.to_excel("../data/SHFE_Shit_target.xlsx", index=False)

    # DCEOptionData.traversal(trade_date=trade_date)
    # print(DCEOptionData.target)
    # DCEOptionData.target.to_excel("../data/DCE_target1008.xlsx", index=False)

    # GFEXOptionData.traversal(trade_date="20240910")
    # print(GFEXOptionData.target)
    # GFEXOptionData.target.to_excel("../data/GFEX_target.xlsx", index=False)

# option_commodity_contract_table_sina_df = ak.option_commodity_contract_table_sina(symbol="豆粕期权", contract="m2501")
# print(option_commodity_contract_table_sina_df)


# print("看涨合约买量求和")
# print(option_commodity_contract_table_sina_df["看涨合约-买量"].sum())


# option_commodity_hist_sina_df = ak.option_commodity_hist_sina(symbol="m2411C3350")
# print(option_commodity_hist_sina_df)
