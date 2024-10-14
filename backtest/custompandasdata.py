import backtrader as bt


class CustomPandasData(bt.feeds.PandasData):
    # Add 'Amount' field to the standard data fields
    lines = ('Amount','Delta')
    params = (
        ('Amount', -1),
        ('Delta', -1),
    )
