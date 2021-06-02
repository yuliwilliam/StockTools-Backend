import sys
sys.path.append('./')

import base64
import time

from utils.utils import *

logger = initialize_logger('traceoption_scraper.py')


def fetch_all_data():
    base_url = 'https://traceoption.com'
    api_url = 'https://api.traceoption.com'

    email = os.getenv('TRACEOPTION_EMAIL')
    password = os.getenv('TRACEOPTION_PASSWORD')
    base64_encoded_credentials = (base64.b64encode(('{}:{}'.format(email, password)).encode())).decode()

    with requests.Session() as s:
        headers = {
            'Host': 'api.traceoption.com',
            'Authorization': 'Basic ' + base64_encoded_credentials
        }
        res = s.post(base_url + '/v1.0/user/login?sign=web',
                     headers=headers)
        token = res.json()['entities']['token']

        headers = {
            'Authorization': token,
        }
        parameters = {
            'sign': 'web',
            'limit': 10,
            # 'cursor': '',
            # 'sector': 'EQUITY'  # EQUITY(i.e. stock) or ETF
        }

        sectors = ['stock', 'etf']
        for sector in sectors:
            parameters['cursor'] = ''
            parameters['sector'] = 'ETF' if sector == 'etf' else 'EQUITY'
            count = 0
            continue_fetch = True
            while continue_fetch:
                res = s.get(api_url + '/v1.0/user/options/living', params=parameters, headers=headers)
                parameters['cursor'] = res.json()['cursor']
                results = res.json()['entities']
                for result in results:
                    continue_fetch = post_to_mongodb(result, sector)
                    count += 1 if continue_fetch else 0
            logger.info('added {} new {} data to database'.format(sector, count))


def post_to_mongodb(data, sector):
    data_date = get_est_time().fromtimestamp(data['received']).date()
    curr_date_collection = get_mongodb_instance()['flow']['{} {}'.format(data_date, sector)]
    curr_ticker_collection = get_mongodb_instance()['tickers']['{}'.format(data['symbol'])]

    inserted = False
    if data_date == get_est_time().date() and curr_date_collection.find_one({'id': data['id']}) is None:
        data['received'] += 15 * 60
        curr_date_collection.insert_one(data)
        inserted = True
    if data_date == get_est_time().date() and curr_ticker_collection.find_one({'id': data['id']}) is None:
        data['received'] += 15 * 60
        curr_ticker_collection.insert_one(data)
        inserted = True
    return inserted


if __name__ == '__main__':
    logger.info('started traceoption web scarper')
    while True:
        if in_trading_days() and in_trading_hours():
            try:
                fetch_all_data()
            except Exception as e:
                send_notification_email(eval(os.getenv('NOTIFICATION_RECEIVER_EMAIL')),
                                        format_email_message(filename='traceoption_scraper.py', exception=e))
        time.sleep(int(os.getenv('SLEEP_BETWEEN_FETCH')))  # sleep 1 minute
