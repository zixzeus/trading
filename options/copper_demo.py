import QuantLib as ql

# 假设的市场数据
underlying_price = 67360  # 标的资产价格
strike_price = 60000 # 执行价格
volatility = 0.1165 # 波动率
risk_free_rate = 0.015  # 无风险利率
maturity_date = ql.Date(24, 11, 2023)  # 到期时间
calculation_date = ql.Date(4, 11, 2023)  # 计算日期

# 构建日期计算和日历
calendar = ql.China()
day_count = ql.Actual365Fixed()
calculation_date = calendar.adjust(calculation_date)
ql.Settings.instance().evaluationDate = calculation_date

# 创建欧式期权
payoff = ql.PlainVanillaPayoff(ql.Option.Put, strike_price)
exercise = ql.EuropeanExercise(maturity_date)
option = ql.VanillaOption(payoff, exercise)

# 使用Black-Scholes模型定价
spot_handle = ql.QuoteHandle(ql.SimpleQuote(underlying_price))
flat_ts = ql.YieldTermStructureHandle(ql.FlatForward(calculation_date, risk_free_rate, day_count))
flat_vol_ts = ql.BlackVolTermStructureHandle(ql.BlackConstantVol(calculation_date, calendar, volatility, day_count))
bs_process = ql.BlackScholesProcess(spot_handle, flat_ts, flat_vol_ts)

option.setPricingEngine(ql.AnalyticEuropeanEngine(bs_process))
option_price = option.NPV()

print(f"Theoretical Option Price: {option_price}")