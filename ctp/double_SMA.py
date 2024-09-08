from ctpbee import CtpBee, CtpbeeApi
from ctpbee.constant import *
from ctpbee import Action
from ctpbee.indicator.indicator import ma
from ctpbee_kline import Kline

class ActionMe(Action):
    def __init__(self, app):
        # 请记住要对父类进行实例化
        super().__init__(app)
        # 通过add_risk_check接口添加风控
        # self.add_risk_check(self.sell)


class DoubleMA(CtpbeeApi):
    fast_period = 2
    slow_period = 10

    def __init__(self, name):
        super().__init__(name)
        self.instrument_set = ['SA501.CZCE']
        self.length = self.slow_period
        self.close = []
        self.pos = 0

    def on_contract(self, contract: ContractData):
        if contract.local_symbol in self.instrument_set:
            self.action.subscribe(contract.local_symbol)

    def on_tick(self, tick: TickData) -> None:
        """
        tick行情触发的时候会调用此函数，你可以通过print来打印它查看详情
        """
        # pass
        print(tick)

    def on_bar(self, bar: BarData):
        print(bar.close_price)
        self.close.append(bar.close_price)
        if len(self.close) <= self.length * 2:
            return
        close_array = self.close[-self.length * 2:]
        fast_ma = ma(close_array, self.fast_period)
        slow_ma = ma(close_array, self.slow_period)
        buy = fast_ma[-1] > slow_ma[-1] and fast_ma[-2] < slow_ma[-2]
        sell = fast_ma[-1] < slow_ma[-1] and fast_ma[-2] > slow_ma[-2]
        if self.pos == 1 and sell:
            self.action.buy_close(bar.close_price, 1, bar)
            self.pos = 0
        elif self.pos == -1 and buy:
            self.action.sell_close(bar.close_price, 1, bar)
            self.pos = 0
        elif buy and self.pos == 0:
            self.pos = 1
            self.action.buy_open(bar.close_price, 1, bar)
        elif sell and self.pos == 0:
            self.pos = -1
            self.action.sell_open(bar.close_price, 1, bar)


def create_app():
    """
    工厂函数 创建app变量并加载相关变量，最后返回
    """
    kline = Kline()
    app = CtpBee("ctpbee", __name__, action_class=ActionMe).with_tools(kline)  # 在此处我们创建我们的核心App。
    info = {
        "CONNECT_INFO": {
            "userid": "230529",
            # "userid": "181290",
            "password": "!1995127Zx",
            "brokerid": "9999",
            "md_address": "tcp://180.168.146.187:10131",
            "td_address": "tcp://180.168.146.187:10130",
            "appid": "simnow_client_test",
            "auth_code": "0000000000000000",
            "product_info": "test"
        },
        "INTERFACE": "ctp",  # 接口声明
        "TD_FUNC": True,  # 开启交易功能
        "XMIN": [1]
    }
    app.config.from_mapping(info)
    double_ma = DoubleMA("double_ma")  # 创建我们的策略实例
    app.add_extension(double_ma)  # 将我们的策略通过app的add_extension接口加入进系统

    return app


if __name__ == "__main__":
    """
    通过ctpbee自己提供的24小时运行模块，让ctpbee能够自行运行程序，并在交易时间段和
    非交易时间段自动上下线
    """
    from ctpbee import hickey

    # 注意你在此处传入的是创建App的函数
    hickey.start_all(create_app)
    # app = create_app()
    # app.start(log_output=True)
