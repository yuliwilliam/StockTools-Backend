import logging
import os
import platform
import sys
from pathlib import Path
import requests
import pymongo
import pytz
import datetime

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def get_est_time():
    tz = pytz.timezone('America/Toronto')
    time = datetime.datetime.now(tz=tz)
    return time


def get_est_time_has_data():
    time = get_est_time()
    if time.weekday() == 0 and time < get_est_time().replace(hour=9, minute=30, second=0, microsecond=0):
        time = (time - datetime.timedelta(days=3))
    elif time.weekday() <= 4 and time < get_est_time().replace(hour=9, minute=30, second=0, microsecond=0):
        time = (time - datetime.timedelta(days=1))
    elif time.weekday() == 5:
        time = (time - datetime.timedelta(days=1))
    elif time.weekday() == 6:
        time = (time - datetime.timedelta(days=2))
    return time.replace(hour=23, minute=59, second=59, microsecond=999999)


def in_trading_hours():
    # If check time is not given, default to current UTC time
    curr_time = get_est_time()
    begin_time = get_est_time().replace(hour=9, minute=0, second=0)
    end_time = get_est_time().replace(hour=17, minute=0, second=0)
    if begin_time < end_time:
        return begin_time <= curr_time <= end_time
    else:  # crosses midnight
        return curr_time >= begin_time or curr_time <= end_time


def in_trading_days():
    return get_est_time().weekday() < 5


def get_mongodb_instance():
    if os.getenv('PRODUCTION') == 'TRUE':
        return pymongo.MongoClient(os.getenv('MONGODB_URL'))
    else:
        return pymongo.MongoClient(os.getenv('MONGODB_URL_AWS'))


def initialize_logger(logger_name=''):
    load_dotenv(Path('./.env'))
    sys.path.append('./')

    if not os.path.exists(os.getenv('LOG_FOLDER')):
        os.makedirs(os.getenv('LOG_FOLDER'))

    if not os.path.exists(os.getenv('LOG_FILE')):
        open(os.getenv('LOG_FILE'), 'w+').close()

    logging.basicConfig(filename=os.getenv('LOG_FILE'), format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler(sys.stdout))

    return logger


def authorize_api_key(api_key):
    return api_key == os.getenv('API_KEY')


def format_number(num):
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    # add more suffixes if you need them
    return '%.2f%s' % (num, ['', 'K', 'M', 'G', 'T', 'P'][magnitude])


def get_selenium_driver_instance():
    curr_os = platform.platform()

    options = Options()
    options.add_argument('--headless')
    options.add_argument('window-size=1920,1080')

    driver = None
    if 'macOS' in curr_os:
        driver = webdriver.Chrome(options=options,
                                  executable_path=os.getenv('WEBDRIVERS_FOLDER') + '/macos/chromedriver')
    elif 'Linux' in curr_os:
        driver = webdriver.Chrome(options=options,
                                  executable_path=os.getenv('WEBDRIVERS_FOLDER') + '/linux/chromedriver')
    return driver


def format_email_message(filename='', message='', exception=''):
    email_message = ''
    if filename:
        email_message += 'filename:\n'
        email_message += filename
        email_message += '\n\n'
    if message:
        email_message += 'message:\n'
        email_message += message
        email_message += '\n\n'
    if exception:
        email_message += 'exception:\n'
        email_message += str(exception)
    return email_message


def send_notification_email(receiver_email_list, message):
    api_key = ''
    headers = {
        'Authorization': 'Bearer {}'.format(api_key),
        'Content-Type': 'application/json'
    }
    receivers = [{'email': receiver_email} for receiver_email in receiver_email_list]
    data = {
        'personalizations': [
            {
                'to': receivers,
            }
        ],
        'from': {
            'email': ''
        },
        'subject': 'Scarper Notification at {}'.format(get_est_time()),
        'content': [
            {
                'type': 'text/plain',
                'value': message
            }
        ]
    }
    res = requests.post('https://api.sendgrid.com/v3/mail/send', headers=headers, data=str(data).replace('\'', '"'))
    return res.status_code == 202
