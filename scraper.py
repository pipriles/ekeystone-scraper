#!/usr/bin/env python3
# This script will scrape each product from a list
# Parse the html and write the data
# Then upload it to shopify
# driver.get('https://wwwsc.ekeystone.com/login')

import pandas as pd
import config
import bs4
import re
import json
import argparse

import config
import decode
import myshopify
import util

from urllib.parse import urljoin, urlencode
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

BASE_URL  = 'https://wwwsc.ekeystone.com'

def login(driver):

    if config.KEYSTONE_USER is None \
    or config.KEYSTONE_PASS is None:
        raise Exception('Set credentials!')

    url = urljoin(BASE_URL, '/login')
    driver.get(url)

    username = driver.find_element_by_id('webcontent_0_txtUserName')
    password = driver.find_element_by_id('webcontent_0_txtPassword')

    username.send_keys(config.KEYSTONE_USER)
    password.send_keys(config.KEYSTONE_PASS)

    submit = driver.find_element_by_id('webcontent_0_submit')
    submit.click()

    wait_for_progress(driver)
    return driver.get_cookies()

def wait_for_progress(driver, timeout=600):

    def displayed(driver):
        id_ = '#webcontent_0_upLoginProgress'
        elem = driver.find_element_by_css_selector(id_)
        return elem.is_displayed()

    try:
        # Wait until it is displayed
        wait = WebDriverWait(driver, 30)
        wait.until(displayed)

    except TimeoutException:
        pass

    # Wait until it is not displayed
    wait = WebDriverWait(driver, timeout)
    wait.until_not(displayed)

    driver.implicitly_wait(0.5)

def wait_for_elem_id(driver, id_, timeout=300):

    event = EC.element_to_be_clickable((By.ID, id_))
    wait = WebDriverWait(driver, timeout)
    elem = wait.until(event)
    return elem

def product_html(driver, pid):

    html = None
    url  = urljoin(BASE_URL, '/Search/Detail') 
    url += '?pid={}'.format(pid)
    print(url)

    # Go to product page in ekeystone
    print('Loading product page...')
    driver.get(url) 

    try:
        id_ = 'webcontent_0_row2_0_detailInfo'
        elem = wait_for_elem_id(driver, id_)
        driver.implicitly_wait(0.5)
    
    except TimeoutException:
        print('TimeoutException!', id_)
        return

    except Exception as e:
        print(e)
        return

    html = elem.get_attribute('innerHTML')
    return html

# MCN84697

def update_data(old, new):

    old['my_price']     = new['my_price']
    old['jobber_price'] = new['jobber_price']

    price = new.get('retail_price')

    if price:
        # Increase price by rate%
        # By default it is set to 20%
        price  = util.parse_price(price)
        price += price * config.PRICE_RATE
        old['retail_price'] = price

    old['inventory'] = new['inventory']
    old['inventory_details'] = new['inventory_details']

    return old

def scrape_details(driver, pids):

    # Create dict from pids
    products = read_json(config.DB_FILE)
    mapping  = { x['pid']: x for x in products }
    pending  = pids.copy()

    while pending:

        p = pending.pop()

        # Update status
        print('\nProcessing product', p)
        util.write_status({ 'status': 'scraping', 
            'pending': len(pending), 'target': p })

        # Scrape product from keystone
        html = product_html(driver, p)

        if html is None: 
            print('No html for product', p)
            continue

        # Extract data from html
        # With decode module
        data = decode.product_data(html)

        # Map product from keystone with local
        match = mapping[p]
        print('Matched!', match['title'])

        # Update local "database" with some keys
        # Using reference from pid dict
        update_data(match, data)

        # Use shopify id to update
        # Implement shopify put method
        util.write_status({ 'status': 'updating' })
        myshopify.update_product(match)

        # Save current state
        write_json(config.DB_FILE, products)
        write_queue(pending)

def fetch_queue():
    try:
        pid = []
        with open(config.LOCK_FILE, 'r', encoding='utf8') as fp:
            pid = [ x.rstrip('\n') for x in fp.readlines() ]
    except FileNotFoundError: pass
    if not pid:
        s = myshopify.pids_from_shopify(config.DB_FILE)
        pid = s.tolist()
    return pid

def write_queue(items):
    with open(config.LOCK_FILE, 'w', encoding='utf8') as fp:
        fp.writelines( '%s\n' % x for x in items )

def read_json(filename, *args, **kwargs):
    with open(filename, 'r', encoding='utf8') as fp:
        data = json.load(fp, *args, **kwargs)
    return data

def write_json(filename, data, *args, **kwargs):
    with open(filename, 'w', encoding='utf8') as fp:
        json.dump(data, fp, *args, **kwargs)

def main():

    parser = argparse.ArgumentParser(
        description='Update data from keystone to shopify')

    parser.add_argument('--products', type=str, 
        default=config.DB_FILE, metavar='FILENAME', 
        help='Local products filename')

    parser.add_argument('--price-rate', type=float,
        default=20, metavar='RATE',
        help='Price percentage rate')

    # Not used...
    parser.add_argument('--chrome-path', type=str,
        default='./chromedriver', metavar='PATH',
        help='Chrome driver path')

    args = parser.parse_args()

    config.DB_FILE    = args.products
    config.PRICE_RATE = args.price_rate / 100

    util.write_status({ 'status': 'fetching' })

    # Fetch current products queue
    myshopify.prepare_shop()
    pids = fetch_queue()

    # Next time the file created will be used
    write_queue(pids)

    count = len(pids)
    print(count, 'products pending!')

    # Update status
    util.write_status({ 'status': 'login', 'pending': count, 
        'price_rate': config.PRICE_RATE, 'target': None })

    try:
        options = webdriver.ChromeOptions()
        options.add_argument('headless')

        # Change as you wish
        # I am lazy to add an argument...
        driver = webdriver.Chrome(
                executable_path='./chromedriver',
                options=options)


        # Login into keystone
        print('Login into keystone...')
        login(driver)

        # Process each product
        scrape_details(driver, pids)
        driver.close()

        util.write_status({ 'status': 'ready' })

    except KeyboardInterrupt:
        pass

    except Exception as e:
        print(e)
        # input('Press enter to exit...')

    finally:
        print('\nDone!')

if __name__ == '__main__':
    main()

