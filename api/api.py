import sys

sys.path.append('./')

from flask import Flask
from flask import request

import traceoption_controller
import finviz_controller
import tradingview_controller
import ark_controller
from utils.utils import *

app = Flask(__name__)
logger = initialize_logger('api.py')


@app.route('/api/getlog', methods=['POST'])
def get_log():
    j = request.json
    logger.info('received /api/getlog post request with request form {}'.format(j))
    api_key = j['apikey']

    if not authorize_api_key(api_key):
        logger.info(
            'returned statue code {} to the /api/getlog post request with request form {}'.format(401, j))
        return {'error': 'unauthorized api key'}, 401

    with open(os.getenv('LOG_FILE'), 'rt') as f:
        logger.info(
            'returned statue code {} to the /api/getlog post request with request form {}'.format(200, j))
        return ''.join(f.readlines()[-50:]), 200


@app.route('/api/getnew', methods=['POST'])
def get_new():
    return traceoption_controller.get_new()


@app.route('/api/gettickerobjects', methods=['POST'])
def get_ticker_objects():
    return traceoption_controller.get_ticker_objects()


@app.route('/api/gettickerstring', methods=['POST'])
def get_ticker_string():
    return traceoption_controller.get_ticker_string()


@app.route('/api/getetfreport', methods=['POST'])
def get_etf_report():
    return traceoption_controller.get_etf_report()


@app.route('/api/getdailysummary', methods=['POST'])
def get_daily_summary():
    return traceoption_controller.get_daily_summary()


@app.route('/api/getfrequent', methods=['POST'])
def get_frequent():
    return traceoption_controller.get_frequent()


@app.route('/api/getbullbear', methods=['POST'])
def get_bull_bear():
    return traceoption_controller.get_bull_bear()


@app.route('/api/getinsidernews', methods=['POST'])
def get_insider_news():
    return finviz_controller.get_insider_news()


@app.route('/api/gettickerchart', methods=['POST'])
def get_ticker_chart():
    return tradingview_controller.get_ticker_chart()


@app.route('/api/getarkholdings', methods=['POST'])
def get_ark_holdings():
    return ark_controller.get_ark_holdings()


@app.route('/api/getarktrades', methods=['POST'])
def get_ark_trades():
    return ark_controller.get_ark_trades()


if __name__ == '__main__':
    logger.info('started api')
    app.run(host='0.0.0.0')
