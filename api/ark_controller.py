from utils.utils import *
from flask import request

logger = initialize_logger('ark_controller.py')


# API documentations
# https://arkfunds.io/api#/ARK%20ETFs/etf_holdings_api_v1_etf_holdings_get
# https://github.com/frefrik/ark-invest-api

def get_ark_holdings():
    j = request.json
    logger.info('received /api/getarkholdings post request with request form {}'.format(j))
    api_key = j.get('apikey')

    if not authorize_api_key(api_key):
        logger.info(
            'returned statue code {} to the /api/getarkholdings post request with request form {}'.format(401, j))
        return {'error': 'unauthorized api key'}, 401

    ticker = j.get('ticker').strip().upper()
    parameters = {'symbol': ticker}
    res = requests.get('https://arkfunds.io/api/v1/stock/fund-ownership', params=parameters)
    ownership = res.json()['ownership']
    res = requests.get('https://arkfunds.io/api/v1/stock/trades', params=parameters)
    trades = res.json()['trades'] if res.status_code == 200 else []
    trades_by_funds = {}
    for trade in trades:
        if trade['fund'] in trades_by_funds:
            trades_by_funds[trade['fund']].append(trade)
        else:
            trades_by_funds[trade['fund']] = [trade]

    stringify_data = '{}:\n'.format(ticker)
    for etf in ownership:
        stringify_data += '基金: {}\n'.format(etf['fund'])
        stringify_data += '占比: {}%\n'.format(etf['weight'])
        stringify_data += '排名: {}\n'.format(etf['weight_rank'])
        stringify_data += '持股: {}\n'.format(etf['shares'])
        stringify_data += '价值: {}\n\n'.format(format_number(etf['market_value']))
        if etf['fund'] in trades_by_funds and len(trades_by_funds[etf['fund']]) > 0:
            recent_trade = trades_by_funds[etf['fund']][0]
            sign = '+' if recent_trade['direction'] == 'Buy' else '-'
            stringify_data += '最新变动时间: {}\n\n'.format(recent_trade['date'])
            stringify_data += '最新变动持仓: {}{}\n'.format(sign, recent_trade['shares'])
            stringify_data += '最新变动占比: {}{}%\n\n'.format(sign, recent_trade['etf_percent'])

    stringify_data += '关注我们的公众号: Stock_Airforce'

    if len(ownership) == 0:
        stringify_data = 'ARK暂无持仓{}'.format(ticker)
    stringify_data = stringify_data.strip()

    logger.info('returned statue code {} to the /api/getarkholdings post request with request form {}'.format(200, j))
    return {'stringify_data': stringify_data}, 200


def get_ark_trades():
    j = request.json
    logger.info('received /api/getarktrades post request with request form {}'.format(j))
    api_key = j.get('apikey')

    if not authorize_api_key(api_key):
        logger.info(
            'returned statue code {} to the /api/getarktrades post request with request form {}'.format(401, j))
        return {'error': 'unauthorized api key'}, 401

    limit = 10

    # valid intervals: 1d, 7d, 1m, 3m, 1y, ytd
    interval = '1d'
    if 'interval' in j.keys():
        interval = j.get('interval')

    trades = []
    for etf in eval(os.getenv('ARK_ACTIVE_ETFS')):
        parameters = {'symbol': etf, 'period': interval}
        res = requests.get('https://arkfunds.io/api/v1/etf/trades', params=parameters)
        if res.status_code == 200:
            trades.extend([dict(trade, **{'fund': res.json()['symbol']}) for trade in res.json()['trades']])

    trades = sorted(trades, key=lambda x: x['etf_percent'], reverse=True)
    trades = trades[:10] if len(trades) > limit else trades
    stringify_data = ''
    for trade in trades:
        sign = '+' if trade['direction'] == 'Buy' else '-'
        stringify_data += '时间: {}\n'.format(trade['date'])
        stringify_data += '基金: {}\n'.format(trade['fund'])
        stringify_data += '代码: {}\n'.format(trade['ticker'])
        stringify_data += '持仓: {}{}\n'.format(sign, trade['shares'])
        stringify_data += '占比: {}{}%\n\n'.format(sign, trade['etf_percent'])
    stringify_data += '关注我们的公众号: Stock_Airforce'

    if len(trades) == 0:
        stringify_data = 'ARK今日暂无持仓变动'
    stringify_data = stringify_data.strip()

    logger.info('returned statue code {} to the /api/getarktrades post request with request form {}'.format(200, j))
    return {'stringify_data': stringify_data}, 200
