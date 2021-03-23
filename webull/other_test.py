import pandas as pd
import numpy as np
from webull import paper_webull
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


# s = sched.scheduler(time.time, time.sleep)

#########
#  CHECK IF MARKET IS OPEN
while True:
    # check and see if its 7am
    now = datetime.now()
    day=datetime.today().strftime('%A')
    current_time = now.strftime("%H:%M:%S")
    print('Today is', day, "Current Time is ", current_time)

    if now.hour >= 2:# and now.minute>=30:# and now.hour<=14:# and now.hour<=14:
        print('start')
        break
    else:
        time.sleep(300)

 ###################      

# LOG IN
wb = paper_webull()
result = wb.login('svalenzuela8@miners.utep.edu', 'Svelty+Car0+2o16!', device_name='', mfa='836177')
if result:
    print("Logged In")
else:
    print("get mfa Data")

# get porftolio info
portfolio = wb.get_portfolio()
# print(portfolio['cashBalance'])
# portfolio_size = portfolio['cashBalance']
print(portfolio['usableCash'])
# portfolio_size = portfolio['usableCash']
portfolio_size = 1000
### INITIALIZE
'''
here you want to define your universe
define you strategy parameters
define vareiagle to control trading fequency
schedule functions
'''
# import list of stocks
stocks = pd.read_csv('/home/vrmn/2021/notes/notes_stocks/sp_500_stocks.csv')
# stocks = yf.tickers_nasdaq()
# stocks = yf.tickers_sp500()
# stocks = pd.DataFrame(stocks)
# stocks.rename(columns={0:'Ticker'},inplace=True)
# print(stocks)
# print('')

# print(stocks['Ticker'])



##### EXECUTE A BATCH API CALL AND BUILD A DATAFRAME ################################

def chunks(lst,n):
    ''' yield succesive n-sized chunks from list '''
    for i in range(0 ,len(lst), n):
        yield lst[i:i+n]

symbol_groups = list(chunks(stocks['Ticker'],100))
symbol_strings = []
for i in range(0, len(symbol_groups)):
    symbol_strings.append(','.join(symbol_groups[i]))

########################## Create your dataset
hqm_columns = [
    'Ticker',
    'Price',
    'Number of Shares to Buy',
    'One-Year Price Return',
    'One-year Return Percentile',
    'Six-Month Price Return',
    'Six-Month Return Percentile',
    'Three-Month Price Return',
    'Three-Month Return Percentile',
    'One-Month Price Return',
    'One-Month Return Percentile'
]

hqm_dataframe = pd.DataFrame(columns=hqm_columns)

for symbol_string in symbol_strings:

    batch_api_call_url = f'https://sandbox.iexapis.com/stable/stock/market/batch?symbols={symbol_string}&types=price,stats&token={IEX_CLOUD_API_TOKEN}'
    data = requests.get(batch_api_call_url).json()
    for symbol in symbol_string.split(','):
        hqm_dataframe = hqm_dataframe.append(
            pd.Series(
                [symbol,
                data[symbol]['price'],
                'n/a',
                data[symbol]['stats']['year1ChangePercent'], 
                'n/a', 
                data[symbol]['stats']['month6ChangePercent'],
                'n/a', 
                data[symbol]['stats']['month3ChangePercent'],
                'n/a',
                data[symbol]['stats']['month1ChangePercent'],
                'n/a',
                ], index =hqm_columns),
            ignore_index = True)


################### CALCULATE MOMENTUM PERCENTILES #########################

time_periods = [
    'One-Year',
    'Six-Month',
    'Three-Month',
    'One-Month'
]

hqm_dataframe.fillna(value=0.0, inplace=True)

for row in hqm_dataframe.index:
    for time_period in time_periods:
        change_col = f'{time_period} Price Return'
        percentile_col = f'{time_period} Return Percentile'
        a = hqm_dataframe[change_col]
        b = hqm_dataframe.loc[row, change_col]
        hqm_dataframe.loc[row, percentile_col] = score(a,b)

##################3 
from statistics import mean

for row in hqm_dataframe.index:
    momentum_percentiles = []
    for time_period in time_periods:
        momentum_percentiles.append(hqm_dataframe.loc[row, f'{time_period} Return Percentile'])
    hqm_dataframe.loc[row,'HQM Score'] = mean(momentum_percentiles)

############# select the 50 best momentum stocks

hqm_dataframe.sort_values('HQM Score', ascending = False, inplace=True)
hqm_dataframe = hqm_dataframe[:5]
hqm_dataframe.reset_index(inplace=True, drop=True)

# print(hqm_dataframe)

##### calcuate the number of shares to buy 
position_size = float(portfolio_size)/len(hqm_dataframe.index)
for i in hqm_dataframe.index:
    hqm_dataframe.loc[i,'Number of Shares to Buy']=math.floor(position_size/hqm_dataframe.loc[i,'Price'])
print(hqm_dataframe)

# buy the recommended values from hqm_dataframe.index
print('Alright lets start trading')
while now.hour<=14:
    dataframes = []
    timeframe = 5 #Enter the timeframe in minutes to trade on (e.g. 1,5,15,60) : "
    days_back = 2 
    for symbol in hqm_dataframe.index:
        '''
            Place an order
            price: float (LMT / STP LMT Only)
            action: BUY / SELL / SHORT
            ordertype : LMT / MKT / STP / STP LMT / STP TRAIL
            timeinforce:  GTC / DAY / IOC
            outsideRegularTradingHour: True / False
            stpPrice: float (STP / STP LMT Only)
            trial_value: float (STP TRIAL Only)
            trial_type: DOLLAR / PERCENTAGE (STP TRIAL Only)
            '''
        stock = hqm_dataframe['Ticker'][symbol]
        quant = hqm_dataframe['Number of Shares to Buy'][symbol]
        # print(quant)

        var_name = stock+'df'

        var_name = wb.get_bars(stock=stock, interval='m5', count=int((390*days_back)/timeframe), extendTrading=1)
        dataframes.append((stock,var_name))

    # print(dataframes)
    # print('')

    for tup in dataframes:
        stock, df = tup
        df['MA20'] = df['close'].rolling(20).mean()
        # df['MA50'] = df['close'].rolling(50).mean()
        # df['rsi'] = talib.RSI(df["close"]) 
        df['upper'] = df['MA20'] + 2*(df['close'].rolling(20).std())
        df['lower'] = df['MA20'] - 2*(df['close'].rolling(20).std())
        # df['lowbuf'] = df['lower']*1.03
        # df[['close','MA20','upper','lower','lowbuf']].plot(figsize=(16,6))
        # plt.show()

        #### lol the beginning of a crossover strategy
        # if df['MA20'][-1]>df['MA50'][-1]:
        #     print('kk')

        # print(df['lower'][-1]*1.03)
        if df['close'][-1] <= df['lower'][-1]:
            print(stock)
            wb.place_order(stock=stock, action='BUY', orderType='MKT', enforce='DAY', quant=quant)
            print('price',yf.get_live_price(stock),'lowerbound',df['lower'][-1])
            print('long')
        elif df['close'][-1]>= df['upper'][-1]:
            print('stock')
            wb.place_order(stock=stock, action='SELL', orderType='MKT', enforce='DAY', quant=quant)
            print('price',yf.get_live_price(stock),'upperbound',df['upper'][-1])
            print('short')
        # print(stock)
        # print(df.tail())
        # print('')

    # check if closing time 
    if now.hour >= 14:
        print('All done for today')
        break
    else:
        time.sleep(90)


# for symbol in pos.index:
#         '''
#             Place an order
#             price: float (LMT / STP LMT Only)
#             action: BUY / SELL / SHORT
#             ordertype : LMT / MKT / STP / STP LMT / STP TRAIL
#             timeinforce:  GTC / DAY / IOC
#             outsideRegularTradingHour: True / False
#             stpPrice: float (STP / STP LMT Only)
#             trial_value: float (STP TRIAL Only)
#             trial_type: DOLLAR / PERCENTAGE (STP TRIAL Only)
#             '''
#     # stock = hqm_dataframe['Ticker'][symbol]
#     # quant = hqm_dataframe['Number of Shares to Buy'][symbol]  
#     try:
#         wb.place_order(stock=stock, action='SELL', orderType='MKT', enforce='DAY', quant=quant)


        # def get_current_orders(self):

        # def get_positions(self):

    # stock,df = dataframes

    # print(stock)
    # print(quant)
    # # stock=None, tId=None, price=0, action='BUY', orderType='LMT', enforce='GTC', quant=0, outsideRegularTradingHour=True, stpPrice=None, trial_value=0, trial_type='DOLLAR')


# wb.cancel_all_orders()





### BEFORE TRADING START


# ### HANDLE DATAT Run this every minute


# ####### RUN STRATEGY
