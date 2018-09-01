#!/usr/bin/env python3
# From the pdf report only 373/740 were found
# From this codes there are 417 possible matchs
# - This also matches vendors with same num
#   but there are not in the report
# We could extract these 417 and prepare them to upload to shopify
# The rest we would try to scrape them from keystone again 
# But it is possible that they don't match

import config
import bs4
import re

import pandas as pd
import json
import sys
import itertools

from urllib.parse import urljoin, urlencode
from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import \
        TimeoutException, WebDriverException

BASE_URL  = 'https://wwwsc.ekeystone.com'
DUMP_PATH = './dump.json'
LOG_PATH  = './debug.json'

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

def search_part(driver, part):

    params = {
        'ShowSmartSuggestions': 'true',
        'SearchType': 'parttype',
        'SearchTerm': part
    }

    route = 'Search?' + urlencode(params)
    url = urljoin(BASE_URL, route)
    driver.get(url)

    # Change browser state...
    try:
        query = '.smartSearchSuggestion a'
        first = driver.find_element_by_css_selector(query)
        selected = first.text
        first.click()
    except Exception:
        selected = None

    return selected

def search_part_number(driver, number):

    params = {
        'ShowSmartSuggestions': 'true',
        'SearchType': 'partnumber',
        'SearchTerm': number
    }

    route = 'Search?' + urlencode(params)
    url = urljoin(BASE_URL, route)
    driver.get(url)

    print('Wait 5 secs...')
    driver.implicitly_wait(2)

    for result in scrape_search(driver):
        yield result

def _scrape_part_numbers(numbers, first=10):

    driver = webdriver.Chrome()
    login(driver)

    for num in numbers:
        results = search_part_number(driver, num)
        head = itertools.islice(results, first)
        yield from head

def extract_result(result):

    data = {}

    sinput = result.select_one('input')
    pid = sinput.get('value')
    data['pid'] = pid

    # PHOTO
    simg = result.select_one('img')
    img = simg['src'] if simg else None
    data['img'] = img

    # NAME & NUMBER
    header = result.select_one('.resultsContentHeader')
    spans  = header.select('span')
    
    supplier = [ s.get_text() for s in spans[:-1] ]
    supplier = ' '.join(supplier).strip()
    data['supplier'] = supplier

    mft_part = [ s.get_text() for s in spans[-1:] ]
    mft_part = ' '.join(mft_part).strip()
    data['num'] = mft_part

    # DESCRIPTION
    description = result.select_one('.descriptionLink a')
    description = description.get_text() if description else None
    data['description'] = description

    # RESTRICTION
    restriction = result.select_one('.requiredProductsMessage')
    message = restriction.get_text() if restriction else None

    restriction = result.select_one(".restrictionsText img")
    title = restriction['title'] if restriction else None

    data['restriction'] = message.strip() if message else title

    # PRICE
    sprice = result.select_one('.resultsPricingArea span span')
    price  = sprice.get_text() if sprice else None
    data['price'] = price

    # AVAILABILITY
    sinventory = result.select_one('div.inventoryDiv')
    rows = sinventory.select('tr') if sinventory else []
    availability = {}

    for row in rows:

        skey = row.select_one('.name') 
        sval = row.select_one('.value')

        name  = skey.get_text().strip() if skey else None
        stock = sval.get_text().strip() if sval else None

        if name: 
            name = re.sub(r'[\W]+', '', name)
            availability[name] = stock

    if sinventory and not availability:

        message = sinventory.select_one('.inventory a')
        extra   = sinventory.select_one('td')

        availability  = message.get_text().strip() if message else ''
        availability += (' ' + extra.get_text().strip()) if extra else ''

    data['availability'] = availability

    return data

def scrape_results(html):

    soup = bs4.BeautifulSoup(html, 'html.parser')
    results = soup.select('.resultsStatic')
    return ( extract_result(r) for r in results )

def find_next_page(driver):

    try:
        pages = driver.find_element_by_css_selector('div.pageNumbers')
        after = pages.find_element_by_css_selector('a.activePage + a')
    except Exception:
        after = None
    return after

def wait_for_search(driver, timeout=600):

    def displayed(driver):
        id_ = '#webcontent_0_row2_0_upSearchProgress'
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

def scrape_search(driver):

    while True:

        # Scrape current results
        html = driver.page_source
        yield from scrape_results(html)

        # Check next page
        next_page = find_next_page(driver)

        if next_page is None:
            break

        try:
            # Click next page
            next_page.click()

        except WebDriverException: 
            # Ignore ugly element in the middle
            # of our precious element
            pass

        print('  Waiting for next page...')
        wait_for_search(driver)

def scrape_part_type(driver, part):

    print('- Searching part:', part)
    choosed = search_part(driver, part)

    if choosed is None: 
        return None

    p_type  = { 'subcategory': part }

    # Wait for page to load
    print('  Waiting for search...')
    wait_for_search(driver)

    for result in scrape_search(driver):
        result.update(p_type)
        yield result

def dump_data(filename, data):
    with open(filename, 'w', encoding='utf8') as fl:
        json.dump(data, fl, indent=2)

def scrape_parts(driver, parts):

    debug = { 'count': 0, 'errors': [] } 
    scraped = []

    for p in parts:

        debug['count'] += 1
        try:
            results = scrape_part_type(driver, p)
            for r in results: scraped.append(r)

        except Exception as e:
            err = { 'message': str(e), 'part': p }
            debug['errors'].append(err)
            driver = restore_driver(driver)

        except KeyboardInterrupt:
            break

        finally:
            # Write results
            dump_data(DUMP_PATH, scraped)
            dump_data(LOG_PATH, debug)

            scount = len(scraped)
            dcount = debug['count']

            m  = '\nTOTAL SCRAPED: %s\n'    % scount
            m += 'PART TYPES SCRAPED: %s\n' % dcount
            print(m)

    return scraped

def restore_driver(driver):

    try:
        driver.title

    except WebDriverException:
        print('- Driver recovered!')
        driver = chrome_driver()
        login(driver)

    return driver

def chrome_driver():

    options = webdriver.ChromeOptions()
    options.add_argument('headless')

    driver = webdriver.Chrome(
            executable_path='./chromedriver',
            chrome_options=options)

    return driver

def read_parts(filename):

    with open(filename, 'r', encoding='utf8') as fl:
        return [ l.rstrip() for l in fl ]

def main():

    if len(sys.argv) != 2:
        print('Usage: ./search.py [FILENAME]')
        return

    filename = sys.argv[1]

    print('Starting chrome...')
    driver = chrome_driver()

    print('Login into eKeystone...')
    login(driver)

    parts = read_parts(filename)
    scrape_parts(driver, parts)

if __name__ == '__main__':
    main()

