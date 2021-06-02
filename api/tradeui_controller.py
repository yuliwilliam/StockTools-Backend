from utils.utils import *
from flask import request

logger = initialize_logger('tradeui_controller.py')


def format_data(data):
    template = '时间：{}\n '.format(data['time']) \
               + '代码：{} {} {}\n'.format(data['ticker'],
                                        get_est_time().strptime(data['date_expiration'],
                                                                "%Y-%m-%dT%H:%M:%S.%f%z").date(),
                                        data['put_call']) \
               + '行权价：{}\n'.format(data['strike_price']) \
               + '成交价：{}\n'.format(data['description'].split('Ref=$')[1]) \
               + '合约价：{} @ {}\n'.format(data['volume'], data['price']) \
               + '类型：{}\n'.format(data['option_activity_type']) \
               + '价值：${}\n'.format(format_number(float(data['volume']) * float(data['price']) * 100)) \
               + '信心：{}\n'.format(data['strength'] if 'strength' in data else 0) \
               + '分类：{}'.format(data['underlying_type'])
    return template


def get_new():
    logger.info('received /api/getnew post request with request form {}'.format(request.json))
    j = request.json
    api_key = j.get('apikey')

    if not authorize_api_key(api_key):
        logger.info(
            'returned statue code {} to the /api/getnew post request with request form {}'.format(401, request.json))
        return {'error': 'unauthorized api key'}, 401

    timestamp = float(j.get('timestamp'))
    date = get_est_time().date()
    curr_date_collection = get_mongodb_instance()['flow'][str(date)]

    curr_date_data_after_timestamp = curr_date_collection.find({'fetched_on': {'$gt': timestamp}}, {'_id': 0})
    stringify_data = []
    for data in curr_date_data_after_timestamp:
        stringify_data.append(format_data(data))

    logger.info(
        'returned statue code {} to the /api/getnew post request with request form {}'.format(200, request.json))
    return {"stringify_data": stringify_data, 'timestamp': get_est_time().timestamp()}, 200


def get_ticker_objects():
    logger.info('received /api/gettickerobjects post request with request form {}'.format(request.json))
    j = request.json
    api_key = j.get('apikey')

    if not authorize_api_key(api_key):
        logger.info('returned statue code {} to the /api/gettickerobjects post request with request form {}'.format(401,
                                                                                                                    request.json))
        return {'error': 'unauthorized api key'}, 401

    logger.info('returned statue code {} to the /api/gettickerobjects post request with request form {}'.format(200,
                                                                                                                request.json))
    return {'data': get_ticker(j)}, 200


def get_ticker_string():
    logger.info('received /api/gettickerstring post request with request form {}'.format(request.json))
    j = request.json
    api_key = j.get('apikey')

    if not authorize_api_key(api_key):
        logger.info('returned statue code {} to the /api/gettickerstring post request with request form {}'.format(401,
                                                                                                                   request.json))
        return {'error': 'unauthorized api key'}, 401

    stringify_data = ''
    for data in get_ticker(j):
        stringify_data += format_data(data)
        stringify_data += '\n\n'

    logger.info('returned statue code {} to the /api/gettickerstring post request with request form {}'.format(200,
                                                                                                               request.json))
    return {"stringify_data": stringify_data[:-1]}, 200


def get_ticker(j):
    flow_database = get_mongodb_instance()['flow']
    query = {
        'ticker': j.get('ticker')
    }
    if 'min_price' in j.keys() or 'max_price' in j.keys():
        query['price'] = {}
    if 'min_price' in j.keys():
        query['price']['$gte'] = float(j.get('min_price'))
    if 'max_price' in j.keys():
        query['price']['$lte'] = float(j.get('max_price'))
    if 'confidence' in j.keys():
        query['strength'] = {'$gte': float(j.get('confidence'))}

    dates = [str(get_est_time().date())]
    if 'min_time' in j.keys() and 'max_time' in j.keys():
        min_date = get_est_time().fromtimestamp(float(j.get('min_time'))).date()
        max_date = get_est_time().fromtimestamp(float(j.get('max_time'))).date()
        dates = [str(min_date + datetime.timedelta(days=x)) for x in range((max_date - min_date).days + 1)]
        dates_in_db = [collection.split(' ')[0] for collection in flow_database.list_collection_names()]
        dates = sorted(list(set(dates) & set(dates_in_db)))
        query['updated'] = {'$gte': j.get('min_time'), '$lte': j.get('max_time')}

    data = []
    for date in dates:
        data.extend(list(flow_database[date].find(query, {'_id': 0})))

    return data
