from ctpbee import CtpBee
from ctpbee import CtpbeeApi
from ctpbee.constant import *
from ctpbee_kline import Kline
from ctpbee.indicator.indicator import ma


class DoubleMa(CtpbeeApi):
    fast_period = 2
    slow_period = 10

    def __init__(self, name, code):
        super().__init__(name)
        self.instrument_set = code
        self.close = []
        self.pos = 0
        self.length = self.slow_period

    def on_init(self, init: bool) -> None:  # 初始化完成回调
        self.info("init successful")

    def on_bar(self, bar: BarData) -> None:
        # if bar is not None:
        #     print(bar.interval, bar)
        #     print("the price is",bar.close_price)
        #     self.close.append(bar.close_price)
        if bar is None:
            return
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

    def on_tick(self, tick: TickData) -> None:
        pass
        # print(tick.datetime, tick.last_price)  # 打印tick时间戳以及最新价格
        #
        # # 买开
        # self.action.buy_open(tick.last_price, 1, tick)
        # # 买平
        # self.action.buy_close(tick.last_price, 1, tick)
        # # 卖开
        # self.action.sell_open(tick.last_price, 1, tick)
        # # 卖平
        # self.action.sell_close(tick.last_price, 1, tick)
        #
        # # 获取合约的仓位
        # position = self.center.get_position(tick.local_symbol)
        # print(position)

    def on_contract(self, contract: ContractData) -> None:
        if contract.local_symbol in self.instrument_set:
            self.action.subscribe(contract.local_symbol)  # 订阅行情
            print("合约乘数: ", contract.size)

    def on_trade(self, trade: TradeData) -> None:
        print(trade)

    def on_order(self, order: OrderData) -> None:
        pass


if __name__ == '__main__':
    kline = Kline()
    code = {"zn2410C24000.SHFE", "zn2410.SHFE"}
    app = CtpBee('ctp', __name__).with_tools(kline)
    info = {
        "CONNECT_INFO": {
            "userid": "181290",
            "password": "!1995127Zx",
            "brokerid": "9999",
            "md_address": "tcp://180.168.146.187:10131",
            "td_address": "tcp://180.168.146.187:10130",

            # "md_address": "tcp://180.168.146.187:10211",
            # "td_address": "tcp://180.168.146.187:10201",

            "appid": "simnow_client_test",
            "auth_code": "0000000000000000",
            "product_info": "test",

        },
        "XMIN": [5],
        "INSTRUMENT_INDEPEND": True,
        "INTERFACE": "ctp",
        "TD_FUNC": True,  # Open trading feature
    }
    app.config.from_mapping(info)  # loading config from dict object
    cta = DoubleMa("double_ma", code)
    app.add_extension(cta)
    app.start()
