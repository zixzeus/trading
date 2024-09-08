from scipy.stats import binom

# 设定参数
num_trials = 33  # 试验次数
probability = 0.4  # 每次试验成功的概率

# 生成二项分布对象
binom_distribution = binom(num_trials, probability)

# 计算概率质量函数（PMF） - 以某些特定值为例
for i in range(num_trials + 1):
    probability_mass_function = binom_distribution.pmf(i)
    print(f"在 {i} 次成功的情况下概率为: {probability_mass_function:.4f}")

# 计算累积分布函数（CDF）
successes = 10  # 成功次数
cumulative_distribution = binom_distribution.cdf(successes)
print(f"{successes} 次成功或更少的概率为: {cumulative_distribution:.4f}")