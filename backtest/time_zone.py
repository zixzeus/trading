from datetime import datetime
import pytz

# Assuming your datetime object with GMT timezone
gmt_datetime = datetime(2024, 5, 1, 21, 5, tzinfo=pytz.timezone('Etc/GMT'))

# Convert to Chicago time (Central Time)
chicago_time = gmt_datetime.astimezone(pytz.timezone('America/New_York'))

# if chicago_time.hour<17:
print(chicago_time)

