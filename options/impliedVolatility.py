import QuantLib as ql

# 设置基础参数
expiration_date = ql.Date(17, 12, 2024)  # 期权到期日
spot_price = 3040  # 标的资产当前价格
strike_price = 3800  # 执行价格
dividend_rate = 0.0  # 股息率
option_type = ql.Option.Call  # 期权类型：看涨期权
risk_free_rate = 0.015  # 无风险利率
market_price = 18.5  # 市场上的期权价格

# 设置 QuantLib 的日期结构
calendar = ql.China()
day_count = ql.Actual365Fixed()
today = ql.Date.todaysDate()
ql.Settings.instance().evaluationDate = today

# 创建期权标的物
payoff = ql.PlainVanillaPayoff(option_type, strike_price)

# 设置到期时间
# exercise = ql.EuropeanExercise(expiration_date)
exercise = ql.AmericanExercise(today,expiration_date)
# 创建欧式期权对象
# european_option = ql.VanillaOption(payoff, exercise)
american_option = ql.VanillaOption(payoff, exercise)
# 设置市场数据
spot_handle = ql.QuoteHandle(ql.SimpleQuote(spot_price))
rate_handle = ql.YieldTermStructureHandle(ql.FlatForward(today, risk_free_rate, day_count))
dividend_handle = ql.YieldTermStructureHandle(ql.FlatForward(today, dividend_rate, day_count))

# 初始波动率猜测
initial_volatility = 0.2
volatility_handle = ql.BlackVolTermStructureHandle(ql.BlackConstantVol(today, calendar, initial_volatility, day_count))

# 使用 Black-Scholes-Merton 模型进行期权定价
bsm_process = ql.BlackScholesMertonProcess(spot_handle, dividend_handle, rate_handle, volatility_handle)

# 设置定价引擎
# european_option.setPricingEngine(ql.AnalyticEuropeanEngine(bsm_process))
binomial_steps = 1000
american_option.setPricingEngine(ql.BinomialVanillaEngine(bsm_process, "crr", binomial_steps))
# 计算隐含波动率
# implied_vol = european_option.impliedVolatility(market_price, bsm_process)
implied_vol = american_option.impliedVolatility(market_price, bsm_process)
print(f"隐含波动率: {implied_vol:.2%}")
