from ctpbee import CtpbeeApi, CtpBee
from ctpbee.constant import TradeData, OrderData, ContractData, Exchange
import pandas as pd
from ctpbee_test import DoubleMa
from ctpbee_kline import Kline

data = pd.read_csv("kline.csv")
data = data.drop("Unnamed: 0", axis=1)
data = [list(reversed(data.to_dict("index").values()))]

if __name__ == '__main__':
    code = "rb2401.SHFE"
    app = CtpBee("looper", __name__)
    info = {
        "PATTERN": "looper",
        "LOOPER": {
            "initial_capital": 100000,
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
        "XMIN": [15]

    }
    app.config.from_mapping(info)
    app.add_local_contract(ContractData(local_symbol=code, exchange=Exchange.SHFE, symbol=code.split(".")[0],
                                        size=10, pricetick=1))
    strategy = DoubleMa("ma", code)
    app.add_extension(strategy)
    app.add_data(*data)
    app.start()
    result = app.get_result(report=True, auto_open=True)
