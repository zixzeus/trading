#import the Quant Lib
import QuantLib as ql

# Let the today date whenwe want to value a instrument be
today = ql.Date(15,6,2020)

# we can set evaluationDate in QL as
ql.Settings.instance().evaluationDate = today
print(ql.Settings.instance().evaluationDate);
# prints..June 15th, 2020

# or you can do
today = ql.Date(15,12,2021);
ql.Settings.instance().setEvaluationDate(today)
print(ql.Settings.instance().evaluationDate)

# prints..December 15th, 2021