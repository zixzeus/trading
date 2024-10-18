import pandas as pd
from blinker import Signal

# 定义信号
data_signal = Signal('data_received')
order_signal = Signal('order_executed')


# 数据处理类
class DataHandler:
    def __init__(self):
        self.data = pd.DataFrame()

    def receive_data(self, new_data):
        # 接收新数据
        self.data = pd.concat([self.data, new_data], ignore_index=True)
        data_signal.send(self.data)  # 发送数据接收信号


# 策略类
class Strategy:
    def __init__(self):
        # 连接数据接收信号
        data_signal.connect(self.handle_data)

    def handle_data(self, data):
        # 处理接收到的数据
        print("Received data:\n", data)
        # 示例：发出下单信号
        self.execute_order()

    def execute_order(self):
        print("Executing order...")
        order_signal.send("Buy order executed")  # 发送下单信号


# 执行交易类
class TradeExecutor:
    def __init__(self):
        # 连接下单信号
        order_signal.connect(self.handle_order)

    def handle_order(self, message):
        # 处理下单信号
        print(message)


# 主程序
if __name__ == "__main__":
    data_handler = DataHandler()
    strategy = Strategy()
    trade_executor = TradeExecutor()

    # 模拟接收数据
    new_data = pd.DataFrame({
        'Open': [100, 101],
        'High': [102, 103],
        'Low': [99, 100],
        'Close': [101, 102]
    })

    data_handler.receive_data(new_data)
