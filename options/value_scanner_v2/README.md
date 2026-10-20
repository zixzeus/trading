# OTM Value Scanner v2 — 只读日行情诊断

这是独立实现，未修改旧 `day_option_analysis.py`，不接触账户，不产生下单指令。

## 判断原则

- 低绝对权利金不是低估；Delta 不是实际获利概率。删除 `delta × ATM close / close`、expected return 和 Kelly 推导。
- 真正的可交易相对低估需要同一时刻可执行的 ask、bid、期货价格、手续费、滑点、保证金/资金占用及退出假设。每日行情不具备这些，因此 `trade_signal` 永远为 False。
- 日行情结算价常含交易所模型/清算处理。用结算价反解IV再拟合微笑，可能只是在测量同一结算模型的光滑性，不能证明独立 alpha。
- 当下输出分层：质量诊断 → 未验证的低IV形态假设 → 有正确F/到期/风格/最小变动价位支持的理论相对价值观察项。后两层都不是买入建议；零候选也是有效结果。

## 输入与严格边界

`--input` 接受此次保存的三个交易所官方原始响应，以及请求日志。日期与官方响应中的日期核对，记录原始字节SHA256。覆盖交易所合约全表，而非旧算法选定品种。原始文件名是此次存档的固定名称，其他日期需要同样的存档格式。

`--futures` 接受官方同日未来合约表，字段为 `contract_id, trade_date, settle, source` 等。普通代码严格按品种+原生月份字符串匹配，郑商所3位年份不擅自扩展；MS是独立系列，不去掉后缀来猜标的。OTM仅由 K>F（call）或K<F（put）判定，等于F不是OTM。此处F是结算参考价，不代表盘中当前虚实值。

`--metadata` 使用合约级CSV：`exchange,contract,underlying_verified,future,future_date,future_source,expiry,style,rate,metadata_source,tick_size`。其中 exchange为 SHFE_INE/CZCE/GFEX；underlying_verified是标的合约代码字符串而非布尔值；expiry为ISO日期；style必须为American/European。期权交割月份绝不作为到期日。

SHFE/INE精确到期、tick来自官方ContractBaseInfo；美式风格来自官方合约/制度文件。其他交易所未核实精确到期时不定价。利率为明确场景假设而非市场观测；本次使用2%连续复利，不能把该假设隐去。

## 估值与拟合

- 欧式：Black-76；美式：期货零漂移CRR树（不是股票q=0），逐节点比较继续持有与立即行权。N与N+1平均降低奇偶误差，默认N=300；候选额外比较2N/2N+1，保守价与中心价都检查。
- 时长为同一日内时点约定下的ACT/365F日期差；不模拟盘中剩余小时、交易日时钟、完整利率曲线。
- 正成交量≥10、持仓≥20、正收盘/结算价；tick已知时剔除≤5 tick的尾部。阈值是保守预设，未通过历史收益回测校准。
- 同交易所、同系列、同方向、同IV来源、同到期和风格分组；每个目标从拟合样本彻底剔除。最多12个最近strike、至少8个；两侧至少各2个有效锚点，Huber降权后仍需满足。
- 在log(K/K_target)上局部二次Huber稳健拟合。F在同系列坐标差中抵消，但OTM和模型定价仍需要真实F。
- 不确定性包络取残差/杠杆修正、线性vs二次敏感性、0.5个波动率百分点下限的最大值。这不是统计置信区间、显著性检验或真实收益概率。
- IV缺口必须超过2个波动率百分点及2倍包络。模型层还要求保守理论价差大于2tick和3倍树网格差；没有ask仍然不产生交易信号。
- 同系列同方向结算价单调性/凸性异常会标记所有相关腿并排除其拟合资格。未知道tick时严格检测会把舍入误差也排除，这是保守降级；不能据此声称可套利。
- CZCE已公布IV如无法核实其模型口径，只做形态诊断，不混入独立反解IV基准，不把缺失元数据强行补齐。

## 复现

在仓库根目录安装 numpy、pandas、scipy 后：

```sh
python -m options.value_scanner_v2.prepare_metadata --folder ../option-metadata-20261019 --output ../option-metadata-20261019/prepared_metadata_v2.csv --rate 0.02
python -m unittest discover -s options/value_scanner_v2/tests -v
python -m options.value_scanner_v2.scanner --input ../options-results-20261019 --date 20261019 --futures ../option-metadata-20261019/underlying_futures_20261019.csv --metadata ../option-metadata-20261019/prepared_metadata_v2.csv --output ../options-v2-results-20261019/full
```

输入可离线运行，不导入akshare、CTP或旧计算器，不写入原始输入。`diagnostics.csv` 为全表，另有质量/覆盖、理论观察项、未验证假设、旧筛选逐条审计、summary与manifest。所有金额是报价点数，未冒称每手货币金额。

## 明确未完成的研究验证

没有历史样本外/滚动验证、成交成本、买卖盘口、成交概率、IV模型口径全市场验证、完整calendar-spread套利检验、全交易所精确到期信息。只有下一步补齐这些数据并做样本外证据，才能把观察名单升级成可执行策略。当天0候选不等于市场没有机会。
