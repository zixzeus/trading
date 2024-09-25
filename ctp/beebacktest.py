from ctpbee import CtpbeeApi, CtpBee
from ctpbee.constant import TradeData, OrderData, ContractData, Exchange
import pandas as pd
from double_SMA import DoubleMA
from utils.basic import read_shfe_data
from ctpbee_kline import Kline

# data = pd.read_csv("kline.csv")
# data = data.drop("Unnamed: 0", axis=1)
# data = [list(reversed(data.to_dict("index").values()))]

data = read_shfe_data("../data/MarketData_Year_2024")
# data = pd.read_excel("../data/MarketData_Year_2024/market_date_test.3.xlsx")
data = data[data["Contract"]=="ag2405"]
data['Contract'] = data['Contract'].apply(lambda x: f"{x}.SHFE")
data['Date'] = pd.to_datetime(data['Date'], format='%Y%m%d')
data['Date'] = data['Date'].apply(lambda x: x.replace(hour=14, minute=30, second=0))
data.rename(
    columns={"Contract": "local_symbol", "Date": "datetime", "Open": "open_price", "High": "high_price", "Low": "low_price",
             "Close": "close_price"},
    inplace=True,
)
data = [list(data.to_dict("index").values())]

if __name__ == '__main__':
    # code = "rb2401.SHFE"
    code = "ag2405.SHFE"
    app = CtpBee("looper", __name__)
    info = {
        "PATTERN": "looper",
        "LOOPER": {
            "initial_capital": 10000,
            "margin_ratio": {
                code: 0.00003,
            },
            "commission_ratio": {
                code: {
                    "close": 0.00001,
                    "close_today": 0.00001,
                },
            },
            "size_map": {
                code: 10
            },
        },
        "XMIN": [1]

    }
    app.config.from_mapping(info)
    app.add_local_contract(ContractData(local_symbol=code, exchange=Exchange.SHFE, symbol=code.split(".")[0],
                                        size=10, pricetick=1))
    strategy = DoubleMA("ma", code)
    app.add_extension(strategy)
    app.add_data(*data)
    app.start()
    result = app.get_result(report=True, auto_open=True)
