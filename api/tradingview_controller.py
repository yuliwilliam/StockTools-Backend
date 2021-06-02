import threading
import time
from flask import request
from twocaptcha import TwoCaptcha

from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import urllib.parse as urlparse
from urllib.parse import parse_qs
from utils.utils import *

logger = initialize_logger('tradingview_controller.py')
logged_in_driver = None
last_fetch_time = get_est_time()
chart_cache = {}
mutex = threading.Lock()


def wait_for_ajax(driver):
    wait = WebDriverWait(driver, 10)

    try:
        wait.until(lambda driver: driver.execute_script('return jQuery.active') == 0)
        wait.until(lambda driver: driver.execute_script('return document.readyState') == 'complete')
    except Exception as e:
        pass


def wait_for_presence(driver, by, element):
    wait_for_ajax(driver)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((by, element)))


def wait_for_text_presence(driver, by, element, text):
    wait_for_ajax(driver)
    WebDriverWait(driver, 10).until(EC.text_to_be_present_in_element((by, element), text))


def element_exists(driver, by, element):
    return len(driver.find_elements(by, element)) > 0


def driver_has_quit(driver):
    try:
        driver.title
        return False
    except Exception as e:
        return True


def log_in():
    email = os.getenv('TRADINGVIEW_EMAIL')
    password = os.getenv('TRADINGVIEW_PASSWORD')

    driver = get_selenium_driver_instance()
    driver.get('https://www.tradingview.com/')

    wait_for_presence(driver, By.CSS_SELECTOR, '[class*="tv-header__link--signin"]')
    driver.find_element_by_css_selector('[class*="tv-header__link--signin"]').click()

    wait_for_presence(driver, By.CSS_SELECTOR, '[class*="js-show-email"]')
    driver.find_element_by_css_selector('[class*="js-show-email"]').click()

    wait_for_presence(driver, By.CSS_SELECTOR, '[class="tv-button__loader"]')
    driver.find_element_by_name('username').send_keys(email)
    driver.find_element_by_name('password').send_keys(password)
    driver.find_element_by_css_selector('[class="tv-button__loader"]').click()
    time.sleep(1)

    if element_exists(driver, By.CSS_SELECTOR, '[title="recaptcha challenge"]'):
        # for recaptchav3, grecaptcha.execute(window.RECAPTCHA_SITE_KEY_V3,{action:t})
        url = driver.find_element_by_css_selector('[title="recaptcha challenge"]').get_attribute('src')
        site_key = parse_qs(urlparse.urlparse(url).query)['k'][0]
        solver = TwoCaptcha(os.getenv('2CAPTCHA_API_KEY'))
        result = solver.recaptcha(sitekey=site_key, url=driver.current_url)
        driver.execute_script('document.getElementById("g-recaptcha-response").innerHTML="{}";'.format(result['code']))
        driver.find_element_by_css_selector('[class="tv-button__loader"]').click()
        time.sleep(1)
        
    wait_for_presence(driver, By.CSS_SELECTOR, '[class*="js-user-dropdown"]')

    # get to chart page
    driver.get('https://www.tradingview.com/chart/')
    wait_for_presence(driver, By.ID, 'header-toolbar-symbol-search')

    return driver


def get_ticker_chart():
    j = request.json
    logger.info('received /api/gettickerchart post request with request form {}'.format(j))
    api_key = j.get('apikey')

    if not authorize_api_key(api_key):
        logger.info(
            'returned statue code {} to the /api/gettickerchart post request with request form {}'.format(401, j))
        return {'error': 'unauthorized api key'}, 401

    is_success = False
    retries, max_retries = 0, 2
    chart = {'chart': -2}, 200

    if mutex.locked():
        send_notification_email(eval(os.getenv('NOTIFICATION_RECEIVER_EMAIL')),
                                format_email_message(filename='tradingview_controller.py', message='encountered -2'))
        return chart
    with mutex:
        while not is_success:
            try:
                chart = get_ticker_chart_helper()
                is_success = True
            except Exception as e:
                raise e
                chart = {'chart': -3}, 200
                logger.error(e)
                retries += 1
                is_success = retries >= max_retries
    return chart


def get_ticker_chart_helper():
    j = request.json

    global logged_in_driver, last_fetch_time, chart_cache
    ticker = j.get('ticker').strip().upper().replace('！', '!')

    cache_time_factor, cache_time = 1 / 4, 0
    # 5 mins - 5, 15 mins - 15, 30 mins - 30
    # 1 hour - 60, 4 hours - 240, 1 day - 1D
    interval = '1D'
    if 'interval' not in j.keys():
        interval = '1D'
    elif int(j.get('interval')) == 5:
        interval = '5'
    elif int(j.get('interval')) == 15:
        interval = '15'
    elif int(j.get('interval')) == 30:
        interval = '30'
    elif int(j.get('interval')) == 1:
        interval = '60'
    elif int(j.get('interval')) == 4:
        interval = '240'

    if interval == '1D':
        cache_time = cache_time_factor * 24 * 60 * 60
    else:
        cache_time = cache_time_factor * int(interval) * 60

    num_of_zoom_in = 9
    pine_script_name = 'AirForce-83'

    # remove expired cache
    expired_keys = [key for key, value in chart_cache.items() if get_est_time().timestamp() >= value['expiration']]
    for key in expired_keys:
        del chart_cache[key]

    # if there is a recent search within 5 hours in cache, return from the cache
    for value in chart_cache.values():
        if value['ticker'] == ticker and value['interval'] == interval:
            logger.info(
                'returned statue code {} to the /api/gettickerchart post request with request form {}'.format(200, j))
            return {'chart': value['chart']}, 200

    # if driver never logged in
    if logged_in_driver is None or driver_has_quit(logged_in_driver):
        logged_in_driver = log_in()
    # if last fetch time is previous day, re-login and reset cache
    if (get_est_time() - last_fetch_time).days >= 1:
        logged_in_driver.quit()
        logged_in_driver = log_in()
        chart_cache = {}
    # if log in session expires
    if not element_exists(logged_in_driver, By.CSS_SELECTOR, '[class*="sources"]') \
            or (element_exists(logged_in_driver, By.CSS_SELECTOR, '[class*="sources"]')
                and pine_script_name not in logged_in_driver.find_element_by_css_selector('[class*="sources"]').text):
        logged_in_driver.quit()
        logged_in_driver = None
        raise Exception()

    last_fetch_time = get_est_time()
    driver = logged_in_driver

    # search ticker
    wait_for_presence(driver, By.ID, 'header-toolbar-symbol-search')
    driver.find_element_by_id('header-toolbar-symbol-search').click()
    wait_for_presence(driver, By.CSS_SELECTOR, '[data-role="search"]')
    driver.find_element_by_css_selector('[data-role="search"]').send_keys(ticker)
    wait_for_presence(driver, By.CSS_SELECTOR, '[class*="listContainer"]')

    # check if ticker exists, if not, return -1
    try:
        wait_for_text_presence(driver, By.CSS_SELECTOR, '[class*="listContainer"]', ticker)
    except Exception as e:
        if 'No symbols match your criteria' in driver.find_element_by_css_selector('[class*="dialog"]').text:
            driver.find_element_by_css_selector('[class*="dialog"]').send_keys(Keys.ESCAPE)
            logger.info(
                'returned statue code {} to the /api/gettickerchart post request with request form {}'.format(200, j))
            return {'chart': -1}, 200

    driver.find_element_by_css_selector('[data-role="search"]').send_keys(Keys.RETURN)

    # select time interval
    time.sleep(1)
    wait_for_presence(driver, By.CSS_SELECTOR, '#header-toolbar-intervals [data-role="button"]')
    driver.find_element_by_css_selector('#header-toolbar-intervals [data-role="button"]').click()
    wait_for_presence(driver, By.CSS_SELECTOR, '[data-value="{}"]'.format(interval))
    driver.find_element_by_css_selector('[data-value="{}"]'.format(interval)).click()

    # select time zone
    time.sleep(1)
    wait_for_presence(driver, By.CSS_SELECTOR, '[data-name="time-zone-menu"]')
    driver.find_element_by_css_selector('[data-name="time-zone-menu"]').click()
    wait_for_presence(driver, By.CSS_SELECTOR, '[data-name="menu-inner"]')
    timezone_elements = driver.find_elements(By.CSS_SELECTOR, '[data-name="menu-inner"] tr')
    est_element = \
        [timezone_element for timezone_element in timezone_elements if 'Toronto' in timezone_element.text][0]
    est_element.click()

    # resize the viewing point
    time.sleep(1)
    driver.find_element_by_tag_name('body').send_keys(Keys.ESCAPE)
    action = webdriver.ActionChains(driver)
    action.move_to_element(driver.find_element_by_css_selector('[class*="control-bar__btn--move-left"]'))
    action.perform()
    driver.find_element_by_css_selector('[class*="control-bar__btn--move-left"]').click()
    wait_for_presence(driver, By.CSS_SELECTOR, '[class*="control-bar__btn--turn-button"]')
    driver.find_element_by_css_selector('[class*="control-bar__btn--turn-button"]').click()
    for i in range(num_of_zoom_in):
        try:
            wait_for_presence(driver, By.CSS_SELECTOR, '[class*="control-bar__btn--zoom-in"]')
            driver.find_element_by_css_selector('[class*="control-bar__btn--zoom-in"]').click()
        except Exception:
            pass

    # close all pop up windows
    pop_up_windows = driver.find_elements(By.CSS_SELECTOR, '[class*="close-button"]')
    for pop_up_window in pop_up_windows:
        pop_up_window.click()

    # move away the mouse from chart
    action = webdriver.ActionChains(driver)
    action.move_to_element(
        driver.find_element_by_css_selector('#drawing-toolbar > div > div > div > div > div:nth-child(6)'))
    action.perform()

    # close pop up windows again
    driver.find_element_by_tag_name('body').send_keys(Keys.ESCAPE)

    time.sleep(1)
    wait_for_presence(driver, By.CSS_SELECTOR, '[class*="chart-container single-visible"]')

    chart = driver.find_element_by_css_selector('[class*="chart-container single-visible"]').screenshot_as_base64

    # update cache with the new chart
    chart_cache[get_est_time().timestamp()] = {'ticker': ticker, 'interval': interval, 'chart': chart,
                                               'expiration': get_est_time().timestamp() + cache_time}

    logger.info('returned statue code {} to the /api/gettickerchart post request with request form {}'.format(200, j))
    return {'chart': chart}, 200
