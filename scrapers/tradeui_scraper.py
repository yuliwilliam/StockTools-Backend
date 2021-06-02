import sys
sys.path.append('./')

import time
# from firebase import firebase as fb
from utils.utils import *

logger = initialize_logger('tradeui_scarper.py')


def fetch_all_data():
    base_url = 'https://tradeui.com'
    email = os.getenv('TRADEUI_EMAIL')
    password = os.getenv('TRADEUI_PASSWORD')

    date = get_est_time().date()
    with requests.Session() as s:
        res = s.post(base_url + '/wp-json/jwt-auth/v1/token',
                     data={'email': email, 'password': password, 'username': email})
        if len(res.json()) == 0:
            logger.error('got token login failed, did not log in')
            return []

        token = res.json()['token']
        parameters = {
            "dFrom": "Today",
            "idT": token,
            "date": date,
            "sFrom": date,
            "sTo": date,
            "tickers": "",
            "p": "1",
            "bbo": "false",
            "aao": "false",
            "mp": "999999999",  # row per page, set high to fetch all rows
            "s": "DESC",
            "sb": "",
            "lm": "0",
            "dtemin": "0",
            "dtemax": "9999",
            "pricemin": "0",
            "pricemax": "1000",
            "corp": "All",
            "ctrmin": "0",
            "ctrmax": "10000",
            "rmin": "0",
            "umin": "0",
            "mmin": "0",
            "st": "All",
            "stmin": "0",
            "etfOrStock": "All",
            "expirationSelected": "",
            "minOrder": "0",
            # "action": "grouped",
            # "exp": 1,
        }
        # url = base_url + '/tui_dev?dFrom=Today&idT=' + token + '&date=2020-12-5&sFrom=2020-12-04&sTo=2020-12-04&tickers=&p=1&bbo=false&aao=false&mp=30&s=DESC&sb=&lm=0&dtemin=0&dtemax=9999&pricemin=0&pricemax=1000&corp=All&ctrmin=0&ctrmax=10000&rmin=0&umin=0&mmin=0&st=All&stmin=0&etfOrStock=All&expirationSelected=&minOrder=0&action=grouped'
        res = s.post(base_url + '/tui_dev', params=parameters)
        if res.status_code == 200:
            logger.info('fetched {} data from tradeui.com'.format(len(res.json())))
            return res.json()
        else:
            logger.error('got statue code {} with error {}'.format(res.status_code, res.text.replace('\n', ' ')))
            return []


# def post_to_firebase(curr_day_data):
#     firebase = fb.FirebaseApplication(os.getenv('FIREBASE_URL'), None)
#     date = get_est_time().date()
#     timestamp = get_est_time().timestamp()
#
#     curr_day_data_in_database = firebase.get('/flow/{}/'.format(date), None)
#     curr_day_ids_in_database = [value['id'] for value in curr_day_data_in_database.values()]
#
#     count = 0
#     threads = []
#     for data in curr_day_data:
#         if data['id'] not in curr_day_ids_in_database:
#             data['fetched_on'] = timestamp
#             thread = threading.Thread(target=lambda: firebase.post('/flow/{}/'.format(date), data))
#             threads.append(thread)
#             thread.start()
#             # firebase.post('/flow/{}/'.format(date), data)
#             count += 1
#     for thread in threads:
#         thread.join()
#     logger.info('added {} new data to database'.format(count))


def post_to_mongodb(curr_day_data):
    date = get_est_time().date()
    timestamp = get_est_time().timestamp()

    mongodb = get_mongodb_instance()
    curr_date_collection = mongodb['flow'][str(date)]

    count = 0
    for data in curr_day_data:
        if len((list(curr_date_collection.find({'id': data['id']})))) <= 0:
            data['fetched_on'] = timestamp
            curr_date_collection.insert_one(data)
            count += 1
    logger.info('added {} new data to database'.format(count))


if __name__ == '__main__':
    logger.info('started tradeui web scarper')
    while True:
        if in_trading_days() and in_trading_hours():
            curr_day_data = fetch_all_data()
            post_to_mongodb(curr_day_data)
        time.sleep(int(os.getenv('SLEEP_BETWEEN_FETCH')))  # sleep 3 minutes
