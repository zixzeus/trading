import QuantLib as ql

# Define option parameters
spot_price = 100       # Current price of the underlying asset
strike_price = 100     # Strike price
risk_free_rate = 0.05  # Annual risk-free interest rate
volatility = 0.2       # Volatility of the underlying asset
dividend_yield = 0.02  # Dividend yield
maturity = ql.Date(15, 6, 2025)  # Option maturity date
calculation_date = ql.Date(15, 6, 2024)

# Set the evaluation date
ql.Settings.instance().evaluationDate = calculation_date

# Define the exercise style for American option
payoff = ql.PlainVanillaPayoff(ql.Option.Call, strike_price)
exercise = ql.AmericanExercise(calculation_date, maturity)

# Define the underlying asset, risk-free rate, and volatility
spot_handle = ql.QuoteHandle(ql.SimpleQuote(spot_price))
rate_handle = ql.YieldTermStructureHandle(ql.FlatForward(calculation_date, risk_free_rate, ql.Actual365Fixed()))
vol_handle = ql.BlackVolTermStructureHandle(ql.BlackConstantVol(calculation_date, ql.NullCalendar(), volatility, ql.Actual365Fixed()))
dividend_handle = ql.YieldTermStructureHandle(ql.FlatForward(calculation_date, dividend_yield, ql.Actual365Fixed()))

# Define the Black-Scholes-Merton process for the American option
bsm_process = ql.BlackScholesMertonProcess(spot_handle, dividend_handle, rate_handle, vol_handle)

# Create the American option
american_option = ql.VanillaOption(payoff, exercise)

# Calculate Greeks
delta = american_option.delta()
gamma = american_option.gamma()
theta = american_option.theta()

#see this link explain https://stackoverflow.com/questions/48535148/quantlib-for-python-runtimeerror-vega-not-provided
vega = american_option.vega()
rho = american_option.rho()

# Print Greek values
print(f"Delta: {delta}")
print(f"Gamma: {gamma}")
print(f"Theta: {theta}")
print(f"Vega: {vega}")
print(f"Rho: {rho}")
