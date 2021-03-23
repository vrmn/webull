import pandas as pd
import numpy as np
from webull import webull
# from webull import webull
from datetime import datetime
import time
import sched
import requests  #for api considered gold standard for executing http request 
import math # math formulas
from scipy.stats import percentileofscore as score # makes it easy to calculate percentile scores
from secrets import IEX_CLOUD_API_TOKEN 
import talib
from talib import RSI, BBANDS
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import yahoo_fin.stock_info as yf
import json

wb = webull()
fh = open('webull_credentials.json','r')
credential_data = json.load(fh)
fh.close()

wb._refresh_token = credential_data['refreshToken']
wb._access_token = credential_data['accessToken']
wb._token_expire = credential_data['tokenExpireTime']
wb._uuid = credential_data['uuid']

n_data = wb.refresh_login()

credential_data['refreshToken'] = n_data['refreshToken']
credential_data['accessToken'] = n_data['accessToken']
credential_data['tokenExpireTime'] = n_data['tokenExpireTime']

file = open('webull_credentials.json', 'w')
json.dump(credential_data, file)
file.close()

# important to get the account_id
wb.get_account_id()

portfolio = wb.get_portfolio()
print(portfolio['cashBalance'])


# stuff = str(print(portfolio))
# print(type(stuff))
# print(stuff)
# sorted_portfolio = list.sort(portfolio)

