# v4 API
import urllib
import time
import hashlib
import hmac
import requests
import json
import random
import string

class Exchange():

    methods = {
            'fee':             {'url': 'api/v4/spot/fee', 'method': 'GET', 'private': True},
            'currencies':      {'url': 'api/v4/spot/currencies', 'method': 'GET', 'private': False},
            'trades':          {'url': 'api/v4/spot/trades', 'method': 'GET', 'private': True},
            'balance':         {'url': 'api/v4/spot/accounts', 'method': 'GET', 'private': True},
            'getOrder':        {'url': 'api/v4/spot/orders', 'method': 'GET', 'private': True},
            'open_orders':     {'url': 'api/v4/spot/open_orders', 'method': 'GET', 'private': True},
            'order':           {'url': 'api/v4/spot/orders', 'method': 'POST', 'private': True},
    }

    def gen_sign(self, method, url, query_string=None, payload_string=None):
        key = 'e4b2513251682cc2a752a4264d15ae18'        # key
        secret = '73de68fbfb75c9e88f6b1beae0956b2845c7a1fa24f6e186c547c1cd2bf2ab6d'     # secret

        t = time.time()
        m = hashlib.sha512()
        m.update((payload_string or "").encode('utf-8'))
        hashed_payload = m.hexdigest()
        s = '%s\n%s\n%s\n%s\n%s' % (method, url, query_string or "", hashed_payload, t)
        sign = hmac.new(secret.encode('utf-8'), s.encode('utf-8'), hashlib.sha512).hexdigest()
        return {'KEY': key, 'Timestamp': str(t), 'SIGN': sign}

    def __init__(self, key, secret):
        self.key = key
        self.secret = bytearray(secret, encoding='utf-8')
        self.shift_seconds = 0

    def __getattr__(self, name):
        def wrapper(*args, **kwargs):
            kwargs.update(command=name)
            return self.call_api(**kwargs)
        return wrapper

    def set_shift_seconds(self, seconds):
        self.shift_seconds = seconds

    def call_api(self, **kwargs):
        command = kwargs.pop('command')
        api_url = 'https://api.gateio.ws/' + self.methods[command]['url']

        if self.methods[command]['private']:
            payload = kwargs
            payload_str = urllib.parse.urlencode(payload)
            headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
            query_param = ''
            body = json.dumps(payload)
            sign_url='/'+self.methods[command]['url']
            if  command=='getOrder':
                sign_url += '/' + kwargs.get('order_id')
                query_param='currency_pair='+kwargs.get('currency_pair')
            print('sign_url =',sign_url)
            print('QUERY_PARAM',query_param)
            print('BODY ',body)
            sign_headers = self.gen_sign(self.methods[command]['method'],
                                          sign_url,
                                          query_param,
                                          payload_string="" if self.methods[command]['method'] == 'GET' else body
                                         )
##        print('KWARGS',kwargs)
        if self.methods[command]['method'] == 'GET' and command!=('balance'):
            if  command=='getOrder':
                api_url += '/' + kwargs.get('order_id')
                query_param='currency_pair='+kwargs.get('currency_pair')
                api_url += '?' + query_param
            else:
                api_url += '?' + payload_str
        print(api_url)
            
        headers.update(sign_headers)
        response = requests.request(method=self.methods[command]['method'],
                                url=api_url,
                                headers=headers,
                                data=body
                                )
##        data="" if self.methods[command]['method'] == 'GET' else body
        if 'code' in response.text:
            print(response.text)
        return response.json()


bot=Exchange(
        key = 'e4b2513251682cc2a752a4264d15ae18',
        secret = '73de68fbfb75c9e88f6b1beae0956b2845c7a1fa24f6e186c547c1cd2bf2ab6d'
    )

########################################################################################################################################################

base='ETH' #символ новой монеты

########################################################################################################################################################
quote='USDT'
symbol=str(base + '_' + quote)
depthOfMA=100

listOfPrices=[]
MAList=[]
lastId=''
high=0

TS0=3
TS1=10
TS2=25
TS3=50

SL=10
threshold=0.01

def trade(tSide):
    #ЦЕНА ПОКУПКИ
    initListOfTrades=bot.trades(currency_pair=symbol,limit=1)
    initPrice=initListOfTrades[0].get('price')
    multiplier=1
    if tSide=='buy':
        multiplier=1.2
    elif tSide=='sell':
        multiplier=1/1.2
    tradePrice=float(initPrice)*multiplier
    ##print(initPrice)

    #ОБЪЁМ ПОКУПКИ
    balanceCurrency=0
    balances=bot.balance()
    coin=''
    if tSide=='buy':
        coin=quote
    elif tSide=='sell':
        coin=base
    for i in range(len(balances)):
        if balances[i].get('currency')==coin:
            balanceCurrency=float(balances[i].get('available'))
    print('AVAILABLE ',balanceCurrency,' ',coin)
    if tSide=='buy':
        tradeAmount=balanceCurrency/tradePrice
    elif tSide=='sell':
        tradeAmount=balanceCurrency #balanceCurrency*tradePrice


    #ПОКУПКА
    custom_id=''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
    print(custom_id)
    new_order=bot.order(text='t-' + custom_id,
                    currency_pair=symbol,
                    type='limit',
                    side=tSide,     # 'buy' / 'sell'
                    amount=str(tradeAmount),
                    price=str(tradePrice),
                    )
##    print('NEW_ORDER',new_order)
    return(new_order,initPrice)

new_ord=trade('buy')
print('NEW ORDER!',new_ord)
new_order=new_ord[0]
initPrice=new_ord[1]

#ПРОВЕРКА ПОКУПКИ
time.sleep(1)
new_order_status=''
while new_order_status!='closed':
    new_order_id=new_order.get('id')
    checkOrder=bot.getOrder(order_id=new_order_id,#custom_id
                 currency_pair=symbol)
    print(checkOrder)
    new_order_status=checkOrder.get('status')
    print(new_order_status)
    
#START PRICE временно берётся из текущей цены, в китайском АПИ вместо цены заполнения объём сделки
SP=initPrice
print('START PRICE = ',SP)
##SP='1' 

#ПРОДАЖА
while True:
    #LIST OF TRADES
    if lastId=='':
        listOfTrades=bot.trades(currency_pair=symbol)
    else:
        listOfTrades=bot.trades(currency_pair=symbol,
                                last_id=lastId)
    if len(listOfTrades)>0:
        lastId=listOfTrades[0].get('id')
    listOfTrades.reverse()

    #MOVING AVERAGE
    for i in range(len(listOfTrades)):
        listOfPrices.append(float(listOfTrades[i].get('price')))
        if len(listOfPrices)>depthOfMA:
            listOfPrices.pop(0)
    MA=sum(listOfPrices)/len(listOfPrices)
    MAList.append(MA)
    print('MA = ',MA)
    if len(MAList)>1: print('MAList[-2] = ',MAList[-2])
    #CURRENT PRICE
    CP=listOfPrices[len(listOfPrices)-1]
    print('CP = ',CP)

    #TRAILING STOP
    if max(listOfPrices)>high: high=max(listOfPrices)
    print('HIGH = ',high)
    SP=float(SP)
    print('SP = ',SP)
    if ((high-SP)/SP)>threshold and len(MAList)>1:
        trailingStop0=high - (high - SP)*(TS0/100)
        trailingStop1=high - (high - SP)*(TS1/100)
        trailingStop2=high - (high - SP)*(TS2/100)
        trailingStop3=high - (high - SP)*(TS3/100)
        print('TS0 = ',trailingStop0)
        print('TS1 = ',trailingStop1)
        print('TS2 = ',trailingStop2)
        print('TS3 = ',trailingStop3)
        if CP>(SP*1.5):
            print('50% PROFIT SELL')
            closeTrade=trade('sell')
            print(closeTrade)
            break
        if MAList[-2]>trailingStop0 and MA<trailingStop0:
            print('TRAILING STOP SELL 0')
            closeTrade=trade('sell')
            print(closeTrade)
            break
        if MAList[-2]>trailingStop1 and MA<trailingStop1:
            print('TRAILING STOP SELL 1')
            closeTrade=trade('sell')
            print(closeTrade)
            break
        if MAList[-2]>trailingStop2 and MA<trailingStop2:
            print('TRAILING STOP SELL 2')
            closeTrade=trade('sell')
            print(closeTrade)
            break
        if MAList[-2]>trailingStop3 and MA<trailingStop3:
            print('TRAILING STOP SELL 3')
            closeTrade=trade('sell')
            print(closeTrade)
            break
        

        
    #STOP LOSS
    stopLoss=float(SP)*((100-SL)/100)
    print('SL = ',stopLoss)
    if CP<stopLoss:
        print('STOP LOSS SELL')
        closeTrade=trade('sell')
        print(closeTrade)
        break
        
    print('\nUPD ',time.time())
##    time.sleep(0.1)













