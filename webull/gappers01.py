
import requests, time, re, os
import pandas as pd
from secrets import IEX_CLOUD_API_TOKEN 
from webull import paper_webull, webull
import math
import argparse
from datetime import datetime
import time
import yahoo_fin.stock_info as yf
import json

nasdaq_list = yf.tickers_nasdaq()
sp500_list = yf.tickers_sp500()
now = datetime.now()

# CREDENTIALS
while True:
    ap = argparse.ArgumentParser()
    ap.add_argument("-a", "--acc", required=True,
	    help="input type of account e.i. --acc paper  or --acc real")
    args = vars(ap.parse_args())
    if args['acc'] == 'paper':
        from webull import paper_webull
        wb = paper_webull()
        result = wb.login('svalenzuela8@miners.utep.edu', 'Svelty+9', device_name='', mfa='195001')
        if result:
            print("Logged Into Paper Account")
        else:
            print("get mfa Data")
        break
    elif args['acc'] == 'cash':
        from webull import webull
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
        break

# while True:
#     now = datetime.now()
#     day=datetime.today().strftime('%A')
#     current_time = now.strftime("%H:%M:%S")
#     print('Today is', day, "Current Time is ", current_time)
#     if now.hour == 7 and now.minute>=26:
#     # if now.hour <= 7: # for testing
#         print('lets begin')
#         break
#     else:
#         time.sleep(60)


# stocks = pd.read_csv('/home/vrmn/2021/notes/notes_stocks/sp_500_stocks2.csv')
stocks = nasdaq_list
stocks = pd.DataFrame(stocks)
stocks.rename(columns={0:'Ticker'},inplace=True)
def chunks(lst,n):
    ''' yield succesive n-sized chunks from list '''
    for i in range(0 ,len(lst), n):
        yield lst[i:i+n]


def gappers(stocks,num):



    symbol_groups = list(chunks(stocks['Ticker'],500))
    symbol_strings = []
    for i in range(0, len(symbol_groups)):
        symbol_strings.append(','.join(symbol_groups[i]))

    hqm_columns = ['symbol','lastPrice','netChange','totalVolume','volatility','lowPrice','highPrice']
    hqm_dataframe = pd.DataFrame(columns=hqm_columns)
    for symbol_string in symbol_strings:
        url = 'https://api.tdameritrade.com/v1/marketdata/quotes'
        payload = {'apikey':'FCLFLNW0R2IBBC9NPIRMIRR6WDCFSS2J',
                    'symbol':symbol_string}
        # print(requests.get(url,params=payload))
        data = requests.get(url,params=payload).json()
        for symbol in symbol_string.split(','):
            try:
                hqm_dataframe = hqm_dataframe.append(
                    pd.Series(
                        [symbol,
                        data[symbol]['lastPrice'],
                        (data[symbol]['netChange']/data[symbol]['lastPrice'])*100,
                        data[symbol]['totalVolume'], 
                        data[symbol]['volatility'], 
                        data[symbol]['lowPrice'],
                        data[symbol]['highPrice']
                        ], index =hqm_columns),
                    ignore_index = True)
            except:
                # print('flag')
                continue
    # print(hqm_dataframe)

    
    # FILTER 
    hqm_dataframe = hqm_dataframe[(hqm_dataframe['netChange']> 3)&(hqm_dataframe['lastPrice']<=50)]
    hqm_dataframe.sort_values('totalVolume', ascending = False, inplace=True)
    hqm_dataframe = hqm_dataframe[:num]
    hqm_dataframe.reset_index(inplace=True, drop=True)
    # print(hqm_dataframe)

    return hqm_dataframe
    

def bollingerBand(stock,timeframe):
    

    days_back = 2 
    df = wb.get_bars(stock=stock, interval='m'+str(timeframe), count=int((390*days_back)/timeframe), extendTrading=1)
    df['MA20'] = df['close'].rolling(20).mean()
    # df['MA50'] = df['close'].rolling(50).mean()
    df['upper'] = df['MA20'] + 2*(df['close'].rolling(20).std())
    df['lower'] = df['MA20'] - 2*(df['close'].rolling(20).std())

    # consider if the the price has corss one of the
    bol_buy_signal = None
    bol_sell_signal = None
    if df['open'][-1] <= df['lower'][-1]:
        bol_buy_signal = True
        bol_sell_signal = False
    elif df['open'][-1] > df['lower'][-1]:
        bol_buy_signal = False
        bol_sell_signal = True

    #########################################################
    # considering also the last two candle sticks for entry
    candle_buy_signal = None
    candle_sell_signal = None
    if df['open'][-1] > df['high'][-2]:
        candle_buy_signal = True
        candle_sell_signal = False
    elif  df['open'][-1] < df['low'][-2]:
        candle_buy_signal = False
        candle_sell_signal = True

    return df, bol_buy_signal, bol_sell_signal, candle_buy_signal, candle_sell_signal

# ################ START DAY TRADE #####################
start_day_trade = time.time()
long_trades = {}
short_trades = {}
while now.hour!=14:
    now = datetime.now()
    portfolio = wb.get_portfolio()
    # GET PORTFOLIO
    try:
        portfolio_size = float(portfolio['cashBalance'])
        print('Your Current Real Flows',portfolio_size)
    except:
        portfolio_size = float(portfolio['usableCash'])
        print('Your Current Paper Flows',portfolio_size)

    # CHECK IF A STOCK HAS ALREADY BEEN PURCHASES
    if len(long_trades) == 1 or len(short_trades)==1:
        print('===============BEGINNING OF DAY TRADE==================')
        print('Stock for day pending purchase \n', 
                'long_trades', long_trades, '\n',
                'short trades', short_trades,'\n')
        break
    else:
        # GET LIST OF HQM STOCKS
        # THEN ITERATE THROUGH EACH ONE
        print('===================TOP 5 HQM STOCKS====================')
        start_time = time.time()
        hqm_dataframe = gappers(stocks,5)
        print(hqm_dataframe)
        print('time it took to get gappers')
        print("--- %s seconds ---" % (time.time() - start_time))
        # print(hqm_dataframe)
        for symbol in hqm_dataframe.index:
            # print(symbol)
            # time.sleep(5)
            stock = hqm_dataframe['symbol'][symbol]
            # print(stock)
            start_time = time.time()
            df, bol_buy_signal, bol_sell_signal, candle_buy_signal, candle_sell_signal = bollingerBand(stock,1)
            print('time it took to get signals')
            print("--- %s seconds ---" % (time.time() - start_time))
            print('===================================================\n')
            print('===================',stock,'Signal Report==================')
            print('candle buy signal:  ',candle_buy_signal,'   bol buy signal:  ',bol_buy_signal)
            print('candle sell signal: ',candle_sell_signal,'  bol sell signal: ',bol_sell_signal)
            # print(df.tail(4))
            # if (bol_buy_signal==True) and (candle_buy_signal == True):
            if candle_buy_signal == True:
            # if True: # for testing
                print('\n===============',stock,'purchase Report==========')
                max_loss = portfolio_size *0.02
                long_stop_price = df['close'][-1]*.95
                quant = math.floor(max_loss/(df['close'][-1]-long_stop_price))
                # wb.get_trade_token('022197')
                # wb.place_order(stock=stock, action='BUY', orderType='MKT', enforce='DAY', quant=quant)
                # long_take_profit_price = df['close'][-1]*1.05
                long_take_profit_price = df['low'][-2] # previous red candle low is going to be the stop price 
                curr_price = df['close'][-1]
                long_trades.update({stock:(curr_price,quant, float(long_stop_price), float(long_take_profit_price))})
                print(f'BUYING {quant} shares of {stock} @ ',df['close'][-1])
                print('stop price', float(long_stop_price), 'take profit price', long_take_profit_price)
                print(df.tail(2),'\n')
                if len(long_trades) == 1 or len(short_trades) == 1:
                    print(f'===============PURCHASED {stock}==================')
                    break
    
    # # CHECK IF WRAPPING UP TIME IS NEAR
    if now.hour == 13 and now.minute >= 40:
        print('All done for today')
        wb.cancel_all_orders()
        break
    else:
        time.sleep(20)
        print('=============END OF TRADE START LOOP============\n')

print('start loop complete after')
print("--- %s seconds ---" % (time.time() - start_day_trade))

# ################ FINISH DAY TRADE #######################
while now.hour<14:
    print('=========START OF FINISH LOOP============')
    if len(long_trades) == 0 and len(short_trades)==0:
        print('Remaining Stocks \n', 
                'long_trades', long_trades, '\n',
                'short trades', short_trades,'\n')
        print('=============END OF DAY TRADE=====================')
        break
    else:
        long_list = list(long_trades)
        short_list = list(short_trades)
        start_time = time.time()
        for lon in long_list:
            # time.sleep(2)
            df, bol_buy_signal, bol_sell_signal, candle_buy_signal, candle_sell_signal = bollingerBand(stock,5)
            purchase_price, quant, stop_price, take_profit= long_trades[lon]
            print(lon,'sell pending')
            print('time it took to iterate through long position')
            print("--- %s seconds ---" % (time.time() - start_time))
            if df['close'][-1] >= df['MA20'][-1] or df['close'][-1] < stop_price or candle_sell_signal==True:
            # if df['close'][-1] >= take_profit or df['close'][-1] < stop_price:
            if df['close'][-1] < stop_price or candle_sell_signal==True:
            # if True:  # for testing
                # wb.get_trade_token('022197')
                # wb.place_order(stock=lon, action='SELL', orderType='MKT', enforce='DAY', quant=quant)
                long_trades.clear()
                print(lon,'finally sold')
                print(f'{quant} shares of {lon} bought at {purchase_price}, was sold at',df['close'][-1],'MA20',df['MA20'][-1])
                print('profit',(purchase_price - df['close'][-1])*quant,'\n')
                print(df.tail(2),'\n')
                print('time it took to iterate through long position')
                print("--- %s seconds ---" % (time.time() - start_time))
                if len(long_trades) == 0 and len(short_trades)==0:
                        break

    if now.hour == 13 and now.minute >= 50:
        print('All done for today')
        wb.cancel_all_orders()
        break
    else:
        print('=========END OF TRADE FINISH LOOP============\n')
        time.sleep(20)

print('confirm finish')