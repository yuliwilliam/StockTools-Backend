import sys
sys.path.append('./')

import time
from bs4 import BeautifulSoup
from utils.utils import *

logger = initialize_logger('finviz_scraper.py')


def fetch_all_data():
    url = 'https://finviz.com/insidertrading.ashx'
    headers = {
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_1_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'
    }

    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.content, 'html.parser')
    rows = soup.find_all('tr', {'class': lambda x: x and x.startswith('insider')})
    headers = ['ticker', 'owner', 'relationship', 'date', 'transaction', 'cost', '#shares', 'value',
               '#shares total', 'sec form 4']
    count = 0
    for row in rows:
        columns = row.find_all('td')
        data = {}
        for i, column in enumerate(columns):
            if headers[i] == 'sec form 4':
                text = column.get_text()
                link = column.a.get('href')
                data[headers[i] + ' time'] = text
                data[headers[i] + ' link'] = link
            else:
                text = column.get_text()
                data[headers[i]] = text
        data['sec form 4 timestamp'] = get_est_time().strptime(data['sec form 4 time'], '%b %d %I:%M %p').replace(
            year=get_est_time().year).timestamp()
        data['date timestamp'] = get_est_time().strptime(data['date'], '%b %d').replace(
            year=get_est_time().year).timestamp()
        if not post_to_mongodb(data):
            break
        count += 1
    logger.info('added {} new insider news data to database'.format(count))


def post_to_mongodb(data):
    mongodb = get_mongodb_instance()
    time = get_est_time().fromtimestamp(data['date timestamp'])

    insider_news_by_date_collection = mongodb['insider_news_by_date'][str(time.date())]
    insider_news_by_ticker_collection = mongodb['insider_news_by_ticker'][data['ticker']]

    inserted = False
    if len(list(insider_news_by_date_collection.find(data))) <= 0:
        insider_news_by_date_collection.insert_one(data)
        inserted = True
    if len(list(insider_news_by_ticker_collection.find(data))) <= 0:
        insider_news_by_ticker_collection.insert_one(data)
        inserted = True
    return inserted


if __name__ == '__main__':
    logger.info('started finviz web scarper')
    while True:
        try:
            fetch_all_data()
        except Exception as e:
            send_notification_email(eval(os.getenv('NOTIFICATION_RECEIVER_EMAIL')),
                                    format_email_message(filename='finviz_scraper.py', exception=e))
        time.sleep(int(os.getenv('FINVIZ_SLEEP_BETWEEN_FETCH')))  # sleep 1 minute
