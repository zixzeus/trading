import matplotlib.pyplot as plt
import pandas as pd
import os
import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
# 假设你有包含历史数据的CSV文件，包括'LME镍价格'和'LME镍库存'列
# 请替换'your_data.csv'为实际文件路径



def transfor_period(df,period):
    dfnew = df.resample(period,on="Date").agg({
        "Date":"last",
        "Price": "mean",
        "Inventory": "mean"
    }).dropna()
    return dfnew

class Cobweb:
    def __init__(self,filepath):
        self.file = filepath
        self.data = None
        self._name = ""
        self._period = "M"
        self._marker = None
        self._figsize = (32,32)
        self._fontsize = 8
        self._dpi = 600

    @property
    def name(self):
        return self._name
    @name.setter
    def name(self,new_name):
        self._name = new_name
    @property
    def period(self):
        return self._period
    @period.setter
    def period(self,new_period):
        self._period = new_period

    @property
    def marker(self):
        return self._marker

    @marker.setter
    def marker(self,new_marker):
        self._marker = new_marker

    @property
    def figsize(self):
        return self._figsize

    @figsize.setter
    def figsize(self,new_figsize):
        self._figsize = new_figsize

    @property
    def fontsize(self):
        return self._fontsize

    @fontsize.setter
    def fontsize(self,new_fontsize):
        self._fontsize = new_fontsize

    @property
    def dpi(self):
        return self._dpi

    @dpi.setter
    def dpi(self,new_dpi):
        self._dpi = new_dpi

    def read_file(self):
        self.data = pd.read_csv(filepath,encoding = 'utf-8')
        self.data['Date'] = pd.to_datetime(self.data['Date'])
        # data.reindex(reversed(data.index))
        # 提取日期、LME镍价格和库存数据
        self.data = transfor_period(self.data,self.period)
        return self.data

    def show(self):
        self.data = self.read_file()
        prices = self.data['Price']
        inventories = self.data['Inventory']

        dates = self.data['Date']
        plt.figure(figsize=self.figsize)
        fig, ax = plt.subplots(figsize=self.figsize)
        plt.scatter = ax.scatter(inventories, prices, c=range(len(self.data)), marker=self.marker, cmap='viridis', label='数据点')

        # 添加序号标签

        for i, txt in enumerate(range(1, len(self.data) + 1)):
            ax.text(inventories.iloc[i], prices.iloc[i], dates.iloc[i].strftime("%Y-%m"), fontsize=8, ha='left', va='bottom')

        plt.plot(inventories, prices)
        plt.title(f'{self.name} cobweb graph')
        plt.xlabel(f'{self.name} inventory')
        plt.ylabel(f'{self.name} price')
        plt.grid(True)

        plt.savefig(f"../pictures/{self.name}.png", dpi=self.dpi)
        plt.show()



# def read_file(filepath):
#     data = pd.read_csv(filepath,encoding = 'utf-8')
#     data['Date'] = pd.to_datetime(data['Date'])
#     # data.reindex(reversed(data.index))
#     # 提取日期、LME镍价格和库存数据
#     data = transfor_period(data,"Y")
#     return data


# 绘制图表


if __name__ == '__main__':
    filepath = "../data/ni.csv"
    silverweb = Cobweb(filepath)
    silverweb.name = "ni"
    silverweb.period = "ME"
    silverweb.dpi = 300
    silverweb.figsize = (32,32)
    silverweb.marker = "x"
    silverweb.show()