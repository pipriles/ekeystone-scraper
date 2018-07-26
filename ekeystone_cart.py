#!/usr/bin/env python3

import config
import bs4
import re
import pandas as pd
import sys
import os

from urllib.parse import urljoin, urlencode
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

BASE_URL = 'https://wwwsc.ekeystone.com'
ZIP_CODE = '99501'
PRODUCT_DIR= './dumps/products/'

def config_cookies(driver):
    cookie = { 'name': 'AccessoriesSearchResultsPageSize', 'value': '48' }
    driver.add_cookie(cookie)

def login(driver):

    if config.KEYSTONE_USER is None \
    or config.KEYSTONE_PASS is None:
        raise Exception('Set credentials!')

    driver.get('https://wwwsc.ekeystone.com/login')

    username = driver.find_element_by_id('webcontent_0_txtUserName')
    password = driver.find_element_by_id('webcontent_0_txtPassword')

    username.send_keys(config.KEYSTONE_USER)
    password.send_keys(config.KEYSTONE_PASS)

    submit = driver.find_element_by_id('webcontent_0_submit')
    submit.click()

    config_cookies(driver)
    return driver.get_cookies()

def wait_for_elem_id(driver, id_, timeout=10):

    event = EC.element_to_be_clickable((By.ID, id_))
    wait = WebDriverWait(driver, timeout)
    elem = wait.until(event)
    return elem

def add_product(driver, pid):

    html = None
    url  = urljoin(BASE_URL, '/Search/Detail') 
    url += '?pid={}'.format(pid)
    print(url)

    # Go to product page in ekeystone
    print('Loading product page...')
    driver.get(url) 

    try:
        # Wait to button to be present
        id_  = 'webcontent_0_row2_0_productDetail'
        id_ += 'BasicInfo_addToOrder_lbAddToOrder'
        elem = wait_for_elem_id(driver, id_)
        driver.implicitly_wait(0.5)

    except TimeoutException as e:
        print('TimeoutException:', id_)
        return
    
    # Clicking "Add to Cart" button
    print('Adding to cart', pid)
    html = driver.page_source
    elem.click()

    try:
        # Check for page validation
        id_  = 'webcontent_0_row2_0_productDetail'
        id_ += 'BasicInfo_addToOrder_FitmentValidator_lbAddToOrder'
        elem = wait_for_elem_id(driver, id_, timeout=5)
        driver.implicitly_wait(0.5)

    except TimeoutException as e:
        print('TimeoutException:', id_)
        return

    print('Skip validation...')
    elem.click()

    return html

    # Executing javascript
    target  = 'webcontent_0$row2_0$productDetailBasicInfo$'
    target += 'addToOrder$lbAddToOrder'
    script = "__doPostBack({}, '')".format(target)
    print(script)
    driver.execute_script(script)

def clear_cart(driver):

    url = urljoin(BASE_URL, '/MyCart')
    driver.get(url)

def wait_for_progress(driver, timeout=600):

    id_ = 'webcontent_0_row2_0_upCheckoutProgress'
    event = EC.visibility_of_element_located((By.ID, id_))

    try:
        wait = WebDriverWait(driver, 30)
        wait.until(event)
    except TimeoutException:
        pass

    wait = WebDriverWait(driver, timeout)
    wait.until_not(event)

    driver.implicitly_wait(0.5)

def parse_shipping(soup):

    # Extract options for each product
    options = []
    pids_wh = []
    warehouses = []

    for sp in soup.select('.checkoutWarehouseHeading > span'):
        title = sp.get_text()
        warehouses.append(title)

    for tb in soup.select('.checkoutShippingOptionsGrid > table'):
        opt = [ l.get_text() for l in tb.select('td label') ]
        options.append(opt)

    for parts in soup.select('.checkoutPartGrid'):

        pids = []
        for a in part.select('.checkoutPrimaryPartId a'):
            href = a.get('href')
            match = re.search(r'pid\=(.+)', href)
            pid = match.group(1)
            pids.append(pid)

        pids_wh.append(pids)

    return { wh: { 'products': p, 'options': opt } \
            for wh, p, opt in zip(warehouses, pids_wh, options) }

def calculate_shipping(driver: webdriver.Chrome):

    url = urljoin(BASE_URL, '/Checkout')
    print('Loading checkout page')
    driver.get(url)

    try:
        # Test if page is really checkout page
        if driver.current_url != url:

            print('Redirected!', driver.current_url)
            id_ = 'webcontent_0_row2_0_lbCheckout'
            elem = wait_for_elem_id(driver, id_)
            elem.click()

        id_ = 'webcontent_0_row2_0_dropShipPostalCode'
        elem = wait_for_elem_id(driver, id_)
        elem.clear()
        elem.send_keys(ZIP_CODE)
        
        id_ = 'webcontent_0_row2_0_lbCalculateShipping'
        elem = wait_for_elem_id(driver, id_)

        # Avoid to click the calculate button
        script = "__doPostBack('webcontent_0$row2_0$lbCalculateShipping','')"
        driver.execute_script(script)

        # Wait page to calculate
        wait_for_progress(driver)

    except TimeoutException as e:
        print('TimeoutException!:', id_) 
        return

    # Scrape data here...
    html = driver.page_source
    soup = bs4.BeautifulSoup(html, 'html.parser')
    data = parse_shipping(soup)

    return data

def add_batch(driver, batch):

    for p in batch:
        html = add_product(driver, p)
        if html is None: continue

        print('HTML stored:', p)
        name = 'product_{}.html'.format(p)
        path = os.path.join(PRODUCT_DIR, name)
        with open(path, 'w', encoding='utf8') as fl:
            fl.write(html)

def main():

    if len(sys.argv) != 2:
        print('Usage: ./eKeystone_cart.py [FILENAME]')
        return

    filename = sys.argv[1]
    df = pd.read_csv(filename)

    options = webdriver.ChromeOptions()
    options.add_argument('headless')

    driver = webdriver.Chrome(
            executable_path='./chromedriver',
            chrome_options=options)

    # '--disable-dev-profile'

    # Login to eKeystone
    login(driver)

    # Add product to cart
    # add_product(driver, 'MTH08612')

    pids = df.pid
    add_batch(driver, pids)

    # data = calculate_shipping(driver)
    # print(data)
    input()

if __name__ == '__main__':
    main()

