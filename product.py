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

def add_product(driver, pid):

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

    return driver.page_source

    # Executing javascript
    # target  = 'webcontent_0$row2_0$productDetailBasicInfo$'
    # target += 'addToOrder$lbAddToOrder'
    # script = "__doPostBack({}, '')".format(target)
    # print(script)
    # driver.execute_script(script)

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
        for a in parts.select('.checkoutPrimaryPartId a'):
            href = a.get('href')
            match = re.search(r'pid\=(.+)', href)
            pid = match.group(1)
            pids.append(pid)

        pids_wh.append(pids)

    return { wh: { 'products': p, 'options': opt } \
            for wh, p, opt in zip(warehouses, pids_wh, options) }

def tabular_form(data):

    for key, value in data.items():
        
        shipping = {}
        for o in value['options']:
            opt, price = re.search(r'(.+) \$(.+)', o).groups()
            shipping[opt] = price

        for p in value['products']:
            ret = {}
            ret.update(shipping)
            ret['pid'] = p
            yield ret

def calculate_shipping(driver: webdriver.Chrome, zip_code=ZIP_CODE):

    url = urljoin(BASE_URL, '/Checkout')
    # print('Loading checkout page')
    # driver.get(url)

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
        elem.send_keys(zip_code)
        
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

def scrape_zip_codes(zip_codes):

    driver = webdriver.Chrome()
    login(driver)

    for code in zip_codes:
        data = calculate_shipping(driver, code)
        flat = tabular_form(data)
        df = pd.DataFrame(flat)
        df.to_csv(f'{code}.csv', index=None)

def add_batch(driver, batch):

    for p in batch:
        try:
            html = add_product(driver, p)
            if html is None: continue
        except Exception as e:
            print(e)

def add_products_to_cart(pids):

    driver = webdriver.Chrome()
    login(driver)
    add_batch(driver, pids)
    driver.close()

def scrape_details(driver, products):

    # Remove extracted
    df = pd.read_csv('./extracted.csv')
    extracted = df.pid
    products  = products[~products.isin(extracted)]
    scraped   = []

    for p in products:
        
        html = product_html(driver, p)
        if html is None: continue

        scraped.append(p)
        
        print('HTML stored:', p)
        name = 'product_{}.html'.format(p)
        name = name.replace('/', '$')
        path = os.path.join(PRODUCT_DIR, name)
        with open(path, 'w', encoding='utf8') as fl:
            fl.write(html)

        s = pd.Series(scraped, name='pid')
        print(len(s), 'more!')

        df = pd.concat([extracted, s])
        df.to_csv('./extracted.csv', header=['pid'], index=None)

def main():

    if len(sys.argv) != 2:
        print('Usage: ./eKeystone_cart.py [FILENAME]')
        return

    filename = sys.argv[1]
    df = pd.read_json(filename)

    # options = webdriver.ChromeOptions()
    # options.add_argument('headless')
    # '--disable-dev-profile'

    driver = webdriver.Chrome()
    #         executable_path='./chromedriver',
    #         chrome_options=options)

    try:
        # Login to eKeystone
        login(driver)

        # Add product to cart
        # add_product(driver, 'MTH08612')

        pids = df.pid
        scrape_details(driver, pids)

        # data = calculate_shipping(driver)
        # print(data)

    except Exception as e:
        print(e)
        input('Press enter to continue...')

    finally:
        driver.close()

if __name__ == '__main__':
    main()

