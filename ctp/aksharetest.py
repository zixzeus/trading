import akshare as ak

futures_zh_minute_sina_df = ak.futures_zh_minute_sina(symbol="m2403", period="1")
print(futures_zh_minute_sina_df)


# futures_main_m=ak.futures_main_sina(symbol="M0", start_date="20000101", end_date="20240910")
#
# print(futures_main_m)

option_czce_hist_df = ak.option_czce_hist(symbol="ZC", year="2021")
print(option_czce_hist_df)


# option_czce_hist_df = ak.option_czce_hist(symbol="RM", year="2020")
# print(option_czce_hist_df)
# symbol = 'RB'
# start_day = '2020-01-01'
# end_day = '2023-01-01'
# exchange = 'DCE'
#
# data = ak.futures.get_futures_data(
#     symbol=symbol,
#     start_day=start_day,
#     end_day=end_day,
#     exchange=exchange,
# )

# print(data)