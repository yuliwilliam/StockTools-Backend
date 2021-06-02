from utils.utils import *
from flask import request
import numpy as np

logger = initialize_logger('traceoption_controller.py')


def get_transaction_type(data):
    # data['type'] = -1 -> PUT, 1 -> CALL
    return 'PUT' if data['type'] == -1 else 'CALL'


# 如果这个改了，前端也需要改得到ticker和minute的代码
def format_multi_legs_data(data):
    # green heart for call, red heart for put
    legs_words = ['一腿', '二腿', '三腿', '四腿']

    template = '时间: {} {}\n'.format(get_est_time().fromtimestamp(data[0]['received']).date(),
                                    get_est_time().fromtimestamp(data[0]['received']).time())
    template += '成交: {} {}\n'.format(data[0]['symbol'], data[0]['spot'])
    call_count, put_count = 0, 0
    for i in range(len(data)):
        template += '{}: {} {}\n'.format(legs_words[i], get_transaction_type(data[i]), data[i]['strike'])
        template += '期权: {} {}\n'.format(get_est_time().fromtimestamp(data[i]['expiration']).date(),
                                         format_number(data[i]['size']))
        if get_transaction_type(data[i]) == 'CALL':
            call_count += 1
        if get_transaction_type(data[i]) == 'PUT':
            put_count += 1

    template = '💚' * call_count + '❤️' * put_count + '\n' + template
    template = '📖 策略大单 📖\n' + template

    return template


# 如果这个改了，前端也需要改得到ticker和minute的代码
def format_single_leg_data(data, is_historical):
    expiration_date = get_est_time().fromtimestamp(data['expiration']).date()
    received_time = get_est_time().fromtimestamp(data['received'])
    template = ''

    if is_historical:
        template += '时间: {} {}/{}\n'.format(received_time.time(), received_time.month, received_time.day)
    else:
        template += '时间: {}\n'.format(received_time.time())

    template += '代码: {} {} {}\n'.format(data['symbol'], str(expiration_date).replace('-', '/'),
                                        get_transaction_type(data))
    template += '行权价: {}\n'.format(data['strike'])
    template += '成交价: {}\n'.format(data['spot'])
    template += '价值: {}\n'.format(format_number(data['size']))

    if not is_historical:
        if data['size'] >= 1e6 and np.busday_count(get_est_time().date(), expiration_date) <= 3:
            template = '🚨 末日大单 🚨\n' + template
        # if data['size'] >= 1e8:
        #     template = '[Bomb] 原子弹 [Bomb]\n' + template
        # elif data['size'] >= 1e7:
        #     template = '💰 千万大单 💰\n' + template
        if data['size'] >= 5e6:
            template = '🎩 幕后大单 🎩\n' + template
        elif data['size'] >= 1e6:
            template = '💰 百万大单 💰\n' + template

    return template


def format_data(data, is_historical=False):
    result = []
    # sort by trading size and take the largest four
    data = sorted(data, key=lambda x: x['size'], reverse=True)
    data = data[:4]

    if len(data) > 1:
        result.append(format_multi_legs_data(data))
    else:
        result.append(format_single_leg_data(data[0], is_historical))
    return result


def get_new():
    j = request.json
    logger.info('received /api/getnew post request with request form {}'.format(j))
    api_key = j['apikey']

    if not authorize_api_key(api_key):
        logger.info(
            'returned statue code {} to the /api/getnew post request with request form {}'.format(401, j))
        return {'error': 'unauthorized api key'}, 401

    timestamp = 0
    if 'timestamp' in j:
        timestamp = float(j['timestamp'])

    exclude = [ticker.strip().upper() for ticker in eval(os.getenv('EXCLUDE_TICKERS'))]
    if 'exclude' in j:
        exclude = [ticker.strip().upper() for ticker in j['exclude']]

    date = get_est_time().date()
    query = {'received': {'$gt': timestamp, '$lt': get_est_time().timestamp()}, 'symbol': {'$nin': exclude}}
    if 'minprice' in j.keys() or 'maxprice' in j.keys():
        query['size'] = {}
    if 'minprice' in j.keys():
        query['size']['$gte'] = float(j.get('minprice'))
    if 'maxprice' in j.keys():
        query['size']['$lte'] = float(j.get('maxprice'))
    sectors = []
    if 'sector' not in j.keys() or j.get('sector').lower() == 'stock':
        sectors.append('stock')
    if 'sector' not in j.keys() or j.get('sector').lower() == 'etf':
        sectors.append('etf')

    flow_database = get_mongodb_instance()['flow']
    stringify_data = []
    data_dict = {}
    for sector in sectors:
        curr_date_collection = flow_database['{} {}'.format(date, sector)]
        curr_date_data_after_timestamp = list(curr_date_collection.find(query, {'_id': 0}).sort('received'))
        for doc in curr_date_data_after_timestamp:
            symbol = doc['symbol']
            received = doc['received']
            if symbol not in data_dict:
                data_dict[symbol] = {doc['received']: [doc]}
            elif received in data_dict[symbol]:
                data_dict[symbol][received].append(doc)
            elif received not in data_dict[symbol]:
                data_dict[symbol][received] = [doc]

    result = [data for data_at_received in data_dict.values() for data in data_at_received.values()]
    result = sorted(result, key=lambda x: x[0]['received'])
    for data in result:
        stringify_data.extend(format_data(data))
    if len(stringify_data) == 0:
        return {"stringify_data": stringify_data, 'timestamp': -1}, 200
    stringify_data = [template + '\n关注我们的公众号: Stock_Airforce' for template in stringify_data]

    logger.info(
        'returned statue code {} to the /api/getnew post request with request form {}'.format(200, j))
    return {"stringify_data": stringify_data, 'timestamp': get_est_time().timestamp()}, 200


def get_ticker_objects():
    j = request.json
    logger.info('received /api/gettickerobjects post request with request form {}'.format(j))
    api_key = j.get('apikey')

    if not authorize_api_key(api_key):
        logger.info('returned statue code {} to the /api/gettickerobjects post request with request form {}'.format(401,
                                                                                                                    j))
        return {'error': 'unauthorized api key'}, 401

    logger.info('returned statue code {} to the /api/gettickerobjects post request with request form {}'.format(200,
                                                                                                                j))
    return {'data': get_ticker(j)}, 200


def get_ticker_string():
    j = request.json
    logger.info('received /api/gettickerstring post request with request form {}'.format(j))
    api_key = j.get('apikey')

    if not authorize_api_key(api_key):
        logger.info('returned statue code {} to the /api/gettickerstring post request with request form {}'.format(401,
                                                                                                                   j))
        return {'error': 'unauthorized api key'}, 401

    data = []
    for curr_data in get_ticker(j):
        data.extend(format_data([curr_data], is_historical=True))

    stringify_data = '\n'.join(data) + '\n关注我们的公众号: Stock_Airforce'
    if len(data) == 0:
        stringify_data = '【自动回复】暂无此股票的大宗交易'

    logger.info('returned statue code {} to the /api/gettickerstring post request with request form {}'.format(200, j))
    return {"stringify_data": stringify_data}, 200


def get_ticker(j):
    flow_database = get_mongodb_instance()['flow']

    limit = 100
    if 'limit' in j.keys():
        limit = int(j['limit']) if int(j['limit']) >= 0 else 0

    page = 0
    if 'page' in j.keys():
        page = int(j['page'])

    query = {}
    query['expiration'] = {'$gte': get_est_time().timestamp() - 7 * 24 * 60 * 60}

    ticker = j.get('ticker').strip().upper()
    if ticker == 'ALL':
        exclude = [ticker.strip().upper() for ticker in eval(os.getenv('EXCLUDE_TICKERS'))]
        if 'exclude' in j:
            exclude = [ticker.strip().upper() for ticker in j['exclude']]
        query['symbol'] = {'$nin': exclude}
    else:
        query['symbol'] = ticker

    if 'minprice' in j.keys() or 'maxprice' in j.keys():
        query['size'] = {}
    if 'minprice' in j.keys():
        query['size']['$gte'] = float(j.get('minprice'))
    if 'maxprice' in j.keys():
        query['size']['$lte'] = float(j.get('maxprice'))

    dates_in_db = list(set([collection.split(' ')[0] for collection in flow_database.list_collection_names()]))
    dates = sorted(dates_in_db, reverse=True)
    if 'mintime' in j.keys() and 'maxtime' in j.keys():
        min_date = get_est_time().fromtimestamp(float(j.get('mintime'))).date()
        max_date = get_est_time().fromtimestamp(float(j.get('maxtime'))).date()
        dates = [str(min_date + datetime.timedelta(days=x)) for x in range((max_date - min_date).days + 1)]
        dates = sorted(list(set(dates) & set(dates_in_db)), reverse=True)
        query['received'] = {'$gte': float(j.get('mintime')), '$lte': float(j.get('maxtime'))}

    sectors = []
    if 'sector' not in j.keys() or j.get('sector').lower() == 'stock':
        sectors.append('stock')
    if 'sector' not in j.keys() or j.get('sector').lower() == 'etf':
        sectors.append('etf')

    data = []
    for date in dates:
        for sector in sectors:
            data.extend(list(flow_database['{} {}'.format(date, sector)].find(query, {'_id': 0}).sort('received', -1)))
        if len(data) >= (page + 1) * limit:
            break

    data = sorted(data, key=lambda x: x['received'], reverse=True)
    if (page + 1) * limit > len(data):
        data = data[-limit:]
    else:
        data = data[page * limit:(page + 1) * limit]

    return data


def get_etf_report():
    j = request.json
    logger.info('received /api/getetfreport post request with request form {}'.format(j))
    api_key = j.get('apikey')

    if not authorize_api_key(api_key):
        logger.info('returned statue code {} to the /api/getetfreport post request with request form {}'.format(401,
                                                                                                                j))
        return {'error': 'unauthorized api key'}, 401

    time = get_est_time_has_data()
    ticker = j.get('ticker').strip().upper()
    call_sum, call_count, put_sum, put_count = get_money_flow({'ticker': ticker, 'timestamp': time.timestamp()})

    stringify_data = ''
    if call_sum == 0 and put_sum == 0:
        stringify_data += '今日没有{}的MoneyFlow'.format(ticker)
    else:
        stringify_data += '{}:\nCall 流入 {}\nPut 流入 {}\n\nCall 总计 {} 笔\nPut 总计 {} 笔\n' \
            .format(ticker, format_number(call_sum), format_number(put_sum), call_count, put_count)
        stringify_data += '\n关注我们的公众号: Stock_Airforce'
    logger.info('returned statue code {} to the /api/getetfreport post request with request form {}'.format(200, j))

    return {"stringify_data": stringify_data}, 200


def get_daily_summary():
    j = request.json
    logger.info('received /api/getdailysummary post request with request form {}'.format(j))
    api_key = j.get('apikey')

    if not authorize_api_key(api_key):
        logger.info('returned statue code {} to the /api/getdailysummary post request with request form {}'.format(401,
                                                                                                                   j))
        return {'error': 'unauthorized api key'}, 401

    is_captain = bool(j.get('captain'))
    time = get_est_time_has_data()

    date = time.date()

    limit = 10
    flow_database = get_mongodb_instance()['flow']
    summary_dict = {}
    for sector in ['stock', 'etf']:
        for data in flow_database['{} {}'.format(date, sector)].find():
            ticker = data['symbol']
            if ticker not in summary_dict:
                summary_dict[ticker] = {'PUT': 0, 'CALL': 0}
            summary_dict[ticker][get_transaction_type(data)] += 1
    summary_list = sorted(list(summary_dict.items()), key=lambda x: max(x[1]['PUT'], x[1]['CALL']), reverse=True)

    stringify_data = ''
    if len(summary_list) == 0:
        stringify_data += '今日暂无期权日报'
    else:
        stringify_data += '【班长日报】{}\n\n'.format(date)
        call_sum, call_count, put_sum, put_count = get_money_flow({'timestamp': time.timestamp()})
        bull_bear_index = put_sum / call_sum
        stringify_data += '今日牛熊指数: {0:.2f}\n\n'.format(bull_bear_index)
        stringify_data += '交易活跃标的:\n'
        for summary in summary_list[:limit]:
            stringify_data += '{}, PUT共{}笔, CALL共{}笔\n'.format(summary[0], summary[1]['PUT'], summary[1]['CALL'])
        stringify_data += '\n大盘风向标:\n'
        for ticker in ['SPY', 'QQQ', 'IWM']:
            call_sum, call_count, put_sum, put_count = get_money_flow({'ticker': ticker, 'timestamp': time.timestamp()})
            stringify_data += '{}:\nCall 流入 {}\nPut 流入 {}\n\nCall 总计 {} 笔\nPut 总计 {} 笔\n\n' \
                .format(ticker, format_number(call_sum), format_number(put_sum), call_count, put_count)
        if not is_captain:
            stringify_data += '获取机器人高级权限，加入班长实盘群，请咨询下方微信 TT99329\n关注我们的公众号: Stock_Airforce'
        else:
            stringify_data += '关注我们的公众号: Stock_Airforce'

    logger.info('returned statue code {} to the /api/getdailysummary post request with request form {}'.format(200, j))
    return {'stringify_data': stringify_data.strip()}, 200


def get_money_flow(j):
    date = get_est_time().date()
    query = {}
    if 'timestamp' in j.keys():
        date = get_est_time().fromtimestamp(float(j.get('timestamp'))).date()
    if 'ticker' in j.keys():
        query['symbol'] = j.get('ticker').strip().upper()

    flow_database = get_mongodb_instance()['flow']
    call_sum, call_count, put_sum, put_count = 0, 0, 0, 0
    for sector in ['stock', 'etf']:
        for data in flow_database['{} {}'.format(date, sector)].find(query):
            call_sum += data['size'] if data['type'] == 1 else 0
            put_sum += data['size'] if data['type'] == -1 else 0
            call_count += 1 if data['type'] == 1 else 0
            put_count += 1 if data['type'] == -1 else 0
    return call_sum, call_count, put_sum, put_count


def get_frequent():
    j = request.json
    logger.info('received /api/getfrequent post request with request form {}'.format(j))
    api_key = j.get('apikey')

    if not authorize_api_key(api_key):
        logger.info('returned statue code {} to the /api/getfrequent post request with request form {}'.format(401, j))
        return {'error': 'unauthorized api key'}, 401

    query = {
        'received': {'$gt': float(j['timestamp']), '$lt': get_est_time().timestamp()}
    }

    flow_database = get_mongodb_instance()['flow']
    stock_data_list = list(
        flow_database['{} stock'.format(get_est_time().date())].find(query).sort('received'))

    data_dict = {}
    for stock_data in stock_data_list:
        symbol = stock_data['symbol']
        received = stock_data['received']
        transaction_type = stock_data['type']
        if symbol not in data_dict:
            data_dict[symbol] = {(received, transaction_type): [stock_data]}
        elif not any(
                [((get_est_time().fromtimestamp(received) - get_est_time().fromtimestamp(key[0])).total_seconds() < 120
                  and transaction_type == key[1]) for key in data_dict[symbol].keys()]):
            data_dict[symbol][(received, transaction_type)] = [stock_data]
        else:
            for key in data_dict[symbol].keys():
                if (get_est_time().fromtimestamp(received) - get_est_time().fromtimestamp(
                        key[0])).total_seconds() < 120 and transaction_type == key[1]:
                    data_dict[symbol][key].append(stock_data)

    result = [data for data_at_received in data_dict.values() for data in data_at_received.values() if len(data) >= 3]
    result = sorted(result, key=lambda x: x[0]['received'])
    stringify_data = ['【智能提醒】{} 快速成交 {} 笔 {}'.format(
        data[0]['symbol'], len(data) - (len(data) + 1) % 2, get_transaction_type(data[0])) for data in result]
    logger.info('returned statue code {} to the /api/getfrequent post request with request form {}'.format(200, j))
    return {'stringify_data': stringify_data,
            'timestamp': stock_data_list[-1]['received'] if len(stock_data_list) > 0 else -1}, 200


def get_bull_bear():
    j = request.json
    logger.info('received /api/getbullbear post request with request form {}'.format(j))
    api_key = j.get('apikey')

    if not authorize_api_key(api_key):
        logger.info('returned statue code {} to the /api/getbullbear post request with request form {}'.format(401, j))
        return {'error': 'unauthorized api key'}, 401

    time = get_est_time_has_data()
    call_sum, call_count, put_sum, put_count = get_money_flow({'timestamp': time.timestamp()})
    bull_bear_index = put_sum / call_sum
    stringify_data = '今日牛熊指数: {0:.2f}\n关注我们的公众号: Stock_Airforce'.format(bull_bear_index)
    logger.info('returned statue code {} to the /api/getbullbear post request with request form {}'.format(200, j))
    return {'stringify_data': stringify_data}, 200
