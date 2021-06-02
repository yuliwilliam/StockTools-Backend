from utils.utils import *
from flask import request

logger = initialize_logger('finviz_controller.py')


def get_transaction_symbol(data):
    if data['transaction'] == 'Buy':
        return '+'
    if data['transaction'] == 'Sale':
        return '-'


def format_news(data):
    template = ''
    template += '时间: {}\n'.format(get_est_time().fromtimestamp(data['date timestamp']).date())
    template += '代码: {}\n'.format(data['ticker'])
    template += '股东: {}\n'.format(data['relationship'])
    template += '成交: {}\n'.format(data['cost'])
    template += '价值: {}\n'.format(format_number(float(data['value'].replace(',', ''))))
    template += '变动: {}{:.1%}\n\n'.format(get_transaction_symbol(data), float(data['#shares'].replace(',', '')) / (
            float(data['#shares'].replace(',', '')) + float(data['#shares total'].replace(',', ''))))
    return template


def get_insider_news():
    j = request.json
    logger.info('received /api/getinsidernews post request with request form {}'.format(j))
    api_key = j.get('apikey')

    if not authorize_api_key(api_key):
        logger.info(
            'returned statue code {} to the /api/getinsidernews post request with request form {}'.format(401, j))
        return {'error': 'unauthorized api key'}, 401

    transactions = ['Sale', 'Buy']
    ticker = j.get('ticker').strip().upper()
    format_to_list = 'list' in j.keys() and bool(j.get('list'))
    ticker_news = list((get_mongodb_instance()['insider_news_by_ticker'][ticker].find(
        {'transaction': {'$in': transactions}}).sort('date timestamp', -1)))[:10]

    stringify_data = [format_news(news) for news in ticker_news]
    if format_to_list:
        stringify_data = [data + '关注我们的公众号: Stock_Airforce' for data in stringify_data]
    else:
        if len(stringify_data) <= 0:
            stringify_data = '【自动回复】暂无此股票的内幕交易'
        else:
            stringify_data = ''.join(stringify_data) + '关注我们的公众号: Stock_Airforce'

    logger.info('returned statue code {} to the /api/getinsidernews post request with request form {}'.format(200, j))
    return {"stringify_data": stringify_data}, 200
