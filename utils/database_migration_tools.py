import threading
import time

from utils import *


def post_to_mongodb(data):
    ticker = data['symbol']
    tickers_database = get_mongodb_instance()['tickers']
    if len(list(tickers_database[ticker].find({'id': data}))) <= 0:
        tickers_database[ticker].insert_one(data)


if __name__ == '__main__':
    initialize_logger()
    flow_database = get_mongodb_instance()['flow']
    threads = []

    for collection_name in sorted(flow_database.list_collection_names()):
        print(collection_name)
        for data in flow_database[collection_name].find({}, {'_id': 0}):
            while threading.active_count() >= 100:
                time.sleep(1)
            thread = threading.Thread(target=lambda: post_to_mongodb(data))
            threads.append(thread)
            thread.start()

    for thread in threads:
        thread.join()

