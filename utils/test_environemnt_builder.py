import argparse
import threading
from utils import *


def post_to_mongodb(data, sector):
    data['received'] = get_est_time().fromtimestamp(data['received']).replace(day=get_est_time().day,
                                                                              month=get_est_time().month,
                                                                              year=get_est_time().year).timestamp()
    flow_database['{} {}'.format(get_est_time().date(), sector)].insert_one(data)


if __name__ == '__main__':
    initialize_logger()

    parser = argparse.ArgumentParser()
    parser.add_argument('source_date', metavar='source_date', type=str, nargs='?', default='')
    parser.add_argument('--build', dest='build', action='store_true', default=False)
    parser.add_argument('--destroy', dest='destroy', action='store_true', default=False)

    args = parser.parse_args()
    flow_database = get_mongodb_instance()['flow']
    source_date = args.source_date

    if args.build and source_date != '':
        threads = []
        for sector in ['stock', 'etf']:
            data_list = list(flow_database['{} {}'.format(source_date, sector)].find())
            for data in data_list:
                thread = threading.Thread(target=lambda: post_to_mongodb(data, sector))
                threads.append(thread)
                thread.start()

        for thread in threads:
            thread.join()

    if args.destroy:
        for sector in ['stock', 'etf']:
            flow_database['{} {}'.format(get_est_time().date(), sector)].drop()
