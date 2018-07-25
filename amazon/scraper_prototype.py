#!/usr/bin/env python3

import requests as rq
import json
import pandas as pd
import multiprocessing as mp
import functools
import sys

from urllib.parse import urljoin
from bs4 import BeautifulSoup

BASE_URL = 'https://www.amazon.com/'
HEADERS = { 'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36' }

def pretty(uggly):
    print(json.dumps(uggly, indent=2))

def querify(string):
    return '+'.join(string.split())

def format_search_string_to_url(search_string):
    q = querify(search_string)
    return 'https://www.amazon.com/s/field-keywords={}'.format(q)

def process_tables(tables, keywords):
    # Ensuring all comparisons are caseless
    caseless_keywords = { s.casefold() for s in keywords } 
    result = {}
    for table in tables:
        for child in table.children:
            if child.name == 'tr':
                head = child.th.text.strip().casefold()
                data = child.td.text.strip()
                if not keywords:
                    result[head] = data 
                elif head in caseless_keywords:
                    result[head] = data
    return result	

# Select keywords from a product details tables, 
# the search is case insensitive, 
# if ther is some uppercase keywords, 
# they'll be transformed to lowercase

def from_select(product_url, keywords=[]): 

    caseless_keywords = { s.casefold() for s in keywords }

    url = urljoin(BASE_URL, product_url)
    resp = rq.get(url, headers=HEADERS)
    resp.raise_for_status()
    html = resp.text

    soup = BeautifulSoup(html, 'html.parser')
    prod_details = soup.find('div', id='prodDetails')
    det_bullets = soup.find(id='detail-bullets')
    unscrapable = False

    result = {}

    if prod_details:
        tables = prod_details.find_all('table')
        result = process_tables(tables, caseless_keywords)

    elif det_bullets:
        details = det_bullets.select('div.content > ul > li')
        det_list_list = ( li.text.split(':', 1) for li in details )
        det_tuples = ( (k.strip().casefold(), v.strip()) \
                for k, v in det_list_list )
        result = { k: v for k,v in det_tuples if k in caseless_keywords }

    else:
        print("Couldn't find product details table")
        print("Nor details list in product_url: ", url)
        unscrapable = True
    
    found_keywords = set(result.keys())
    all_data = True if not keywords else found_keywords == caseless_keywords
    some_data = True if not keywords else found_keywords != set()

    result['all_details_extracted'] = all_data
    result['some_details_extracted'] = some_data
    result['product_url'] = url
    result['unscrapable'] = unscrapable 
    # If this boolean is True, that means that the product 
    # was found on amazon but i couldn't scrape the details from it

    return result

def get_product_results(search_string):

    # Request
    url = format_search_string_to_url(search_string)
    res = rq.get(url, headers=HEADERS)
    res.raise_for_status()

    # Parsing html
    soup = BeautifulSoup(res.text, 'html.parser')
    items = soup.select('div[class*="item-container"]')
    results = []

    for i in items:
        result = i.select_one('a[class*="access-detail-page"]')
        if result is not None:
            results.append({ 
                'title': result.h2['data-attribute'],
                'url': result['href'] 
            })

    return results

def search_product_info(search_string, details=[]):

    # first_best_fit(search_string, get_product_results(search_string))
    results = get_product_results(search_string) 
    if not results:
        return { 'found': False }

    url = results[0]['url']
    extracted_data = from_select(url, details)

    return { 
        **extracted_data, 
        'found': extracted_data['some_details_extracted'] 
    }

def build_queries_from_product(product):
    brand = product['supplier']
    subcategory = product['subcategory'].strip()
    number = product['num'][0: product['num'].find('(')].strip()
    yield '{} {}'.format(subcategory, number)
    yield '{} {}'.format(brand, number)

# Search products info, optional, just search some details from products 
# (details = list of keywords of details. 
# example: ['shipping weight', 'product dimensions'])
def search_products(product_list, details=[]):

    for product in product_list:
        yield scrape_product(product, details)

# Make a list of products that haven't been scraped

def filter_scraped(products, scraped):
    pids = { p.get('pid') for p in scraped if p }
    return [ p for p in products if p and p.get('pid') not in pids ]

def dump_data(filename, data):
    with open(filename, 'w', encoding='utf8') as fl:
        json.dump(data, fl, indent=2)

def read_data(filename, default=None):
    try:
        with open(filename, 'r', encoding='utf8') as fl:
            return json.load(fl)
    except FileNotFoundError:
        return default

def scrape_product(product, details=[]):

    result = {}
    search_queries = []
    exceptions = []
    queries = build_queries_from_product(product)

    for q in queries:

        try:
            search_queries.append(q)
            result = search_product_info(q, details)

        except Exception as e:
            exceptions.append(str(e))
            result['found'] = False

        except KeyboardInterrupt:
            pass

        if result['found']: 
            break

    result.update({ 
        'pid': product['pid'],
        'query_strings': search_queries,
        'exceptions': exceptions
    })

    return result

def crawl_products(products, details=[], N=4):

    with mp.Pool(N) as p:
        scraper = functools.partial(scrape_product, details=details)
        yield from p.imap_unordered(scraper, products)

def main():

    if len(sys.argv) != 2:
        print('Usage: ./scraper.py [FILENAME]')
        return

    filename = sys.argv[1]
    products = []
    scraped  = []

    scraped = read_data('amazon.json', [])
    # Assume it is a JSON file
    # products = read_data(filename) 
    # Or read from csv, just to make things more easy
    df = pd.read_csv(filename)
    products = df.to_dict(orient='records')
    products = filter_scraped(products, scraped)

    try:
        # Now using this function it scrapes with 8 threads
        for result in crawl_products(products, N=8):
            scraped.append(result)
            dump_data('amazon.json', scraped)
            pretty(result) # Nope

    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()

