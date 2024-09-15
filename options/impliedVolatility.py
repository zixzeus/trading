import QuantLib as ql
import time
# 设置基础参数
expiration_date = ql.Date(24, 9, 2024)  # 期权到期日
spot_price = 23830  # 标的资产当前价格
strike_price = 24000  # 执行价格
dividend_rate = 0.0  # 股息率
option_type = ql.Option.Call  # 期权类型：看涨期权
risk_free_rate = 0.015  # 无风险利率
market_price = 190  # 市场上的期权价格

# 设置 QuantLib 的日期结构
calendar = ql.China()
day_count = ql.Actual365Fixed()
today = ql.Date.todaysDate()
ql.Settings.instance().evaluationDate = today

# 创建期权标的物
payoff = ql.PlainVanillaPayoff(option_type, strike_price)

# 设置市场数据
spot_handle = ql.QuoteHandle(ql.SimpleQuote(spot_price))
rate_handle = ql.YieldTermStructureHandle(ql.FlatForward(today, risk_free_rate, day_count))
dividend_handle = ql.YieldTermStructureHandle(ql.FlatForward(today, dividend_rate, day_count))

# 初始波动率猜测
initial_volatility = 0.2
volatility_handle = ql.BlackVolTermStructureHandle(ql.BlackConstantVol(today, calendar, initial_volatility, day_count))

# 使用 Black-Scholes-Merton 模型进行期权定价
bsm_process = ql.BlackScholesMertonProcess(spot_handle, dividend_handle, rate_handle, volatility_handle)
# 设置到期时间
exercise = ql.EuropeanExercise(expiration_date)
# 创建欧式期权对象
european_option = ql.VanillaOption(payoff, exercise)
# 设置定价引擎
start_time = time.time()
european_option.setPricingEngine(ql.AnalyticEuropeanEngine(bsm_process))

# 计算隐含波动率
implied_vol = european_option.impliedVolatility(market_price, bsm_process)

delta = european_option.delta()
theta = european_option.thetaPerDay()
gamma = european_option.gamma()
vega = european_option.vega()
rho = european_option.rho()

end_time = time.time()
execution_time = end_time - start_time
print(f"隐含波动率: {implied_vol:.2%}")
print(f"Delta: {delta}")
print(f"Theta: {theta}")
print(f"Gamma", gamma)
print(f"Vega", vega)
print(f"rho", rho)
print("Execution Time: ", execution_time)

start_time1 = time.time()
exercise = ql.AmericanExercise(today, expiration_date)
american_option = ql.VanillaOption(payoff, exercise)
binomial_steps = 1000
american_option.setPricingEngine(ql.BinomialVanillaEngine(bsm_process, "crr", binomial_steps))
implied_vol = american_option.impliedVolatility(market_price, bsm_process)
delta = american_option.delta()
theta = american_option.theta() / 365
gamma = american_option.gamma()
end_time1 = time.time()
print(f"implied_vol: {implied_vol}")
print(f"Delta: {delta}")
print(f"Theta: {theta}")
print(gamma)
execution_time1 = end_time1 - start_time1
print(f"Execution time: {execution_time1} seconds")
# see the link to explain why
# https://stackoverflow.com/questions/48535148/quantlib-for-python-runtimeerror-vega-not-provided
# vega = american_option.vega()
# rho = american_option.rho()
# print(vega)
# print(rho)
