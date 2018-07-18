#!/usr/bin/env python3

import requests as rq
import json
import pandas as pd
import multiprocessing as mp
import functools

from bs4 import BeautifulSoup

def pretty(uggly):
    print(json.dumps(uggly, indent=2))

# More hard coded than select_from function
def get_product_info(product_link):
    tech_table_id = 'productDetails_techSpec_section_1'
    info_table_id = 'productDetails_detailBullets_sections1'
    prod_specs = {}

    res = rq.get(product_link)
    soup = BeautifulSoup(res.text, 'html.parser')

    tech_table = soup.find('table', id=tech_table_id)

    if tech_table is None:
        return prod_specs

    for spec_row in tech_table.children:
        if spec_row.name == 'tr':
            header = spec_row.th.text.strip()
            data = spec_row.td.text.strip()
            prod_specs[header] = data

    info_table = soup.find('table', id=info_table_id)

    if info_table is None:
        return prod_specs

    for info_row in info_table.children:
        if info_row.name == 'tr' \
        and 'Shipping Weight' in info_row.th.text.strip():
            header = info_row.th.text.strip()
            data = info_row.td.text.strip()
            prod_specs[header] = data

    return prod_specs

def querify(string):
    return '+'.join(string.split())

def format_search_string_to_url(search_string):
    q = querify(search_string)
    return 'https://www.amazon.com/s/field-keywords={}'.format(q)

def process_tables(tables, keywords):
    result = {}
    for table in tables:
        for child in table.children:
            if child.name == 'tr':
                head = child.th.text.strip()
                data = child.td.text.strip()
                if keywords == []:
                    result[head] = data 
                elif head.casefold() in caseless_keywords:
                    result[head] = data 
    return result	

# select keywords from a product details tables, the search is case insensitive
def from_select(product_url, keywords=[]): 
    caseless_keywords = [s.casefold() for s in keywords]
    headers = { 'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36' }
    res = rq.get(product_url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    prod_details = soup.find('div', id='prodDetails')
    det_bullets = soup.find(id = 'detail-bullets')
    
    result = {}
    if prod_details:
        tables = prod_details.find_all('table')
        result = process_tables(tables, keywords)
    elif det_bullets:
        details = det_bullets.find_all('li')
        det_tuples = (li.text.split(':', 1) for li in details)
        result = dict((k.strip(), v.strip()) for k,v in det_tuples)
    else:
        print("Couldn't find product details table nor details list in product_url", product_url)
    return result

def get_product_results(search_string):
    # request
    headers = { 'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36' }
    res = rq.get(format_search_string_to_url(search_string), headers=headers)
    res.raise_for_status()
    # parsing html
    soup = BeautifulSoup(res.text, 'html.parser')
    items = soup.select('div[class*="item-container"]')
    results = []
    for i in items:
        result = i.select_one('a[class*="access-detail-page"]')
        if result is not None:
            results.append({ 'title': result.h2['data-attribute'] ,'url': result['href'] })

    return results

def search_product_info(search_string, details=[]):
    results = get_product_results(search_string) # first_best_fit(search_string, get_product_results(search_string))
    return from_select(results[0]['url'], details) if results else None


def build_query_from_product(product):
    supplier = product['supplier'].strip()
    number = product['num'][0: product['num'].find('(')].strip()
    return '{} {}'.format(supplier, number)

# Search products info, optional, just search some details from products 
# (details = list of keywords of details. 
# example: ['shipping weight', 'product dimensions'])
def search_products(product_list, details=[]):

    for product in product_list:
        yield scrape_product(product, details)

# Make a list of products that haven't been scraped

def filter_scraped(products, scraped):
    pids = set(p.get('pid') for p in scraped )
    return [ p for p in products if p.get('pid') not in pids ]

def dump_data(filename, data):
    with open(filename, 'w', encoding='utf8') as fl:
        json.dump(data, fl, indent=2)

def read_data(filename, default=None):
    try:
        with open(filename, 'r', encoding='utf8') as fl:
            return json.load(fl)
    except FileExistsError:
        return default

def scrape_product(product, details=[]):

    search_string = build_query_from_product(product)
    result = search_product_info(search_string, details)
    # found means that there is at least one result in the amazon search

    if result:
        return { 
            'pid': product['pid'],
            'query_string': search_string,
            'found': True,
            **result
        }

    else:
        return {
            'pid': product['pid'],
            'query_string': search_string,
            'found': False,
        }

def crawl_products(products, details=[], N=4):

    with mp.Pool(N) as p:
        scraper = functools.partial(scrape_product, details=details)
        yield from p.imap_unordered(scraper, products)

def main():
    products = []
    scraped  = []

    scraped  = read_data('amazon.json')
    products = read_data('ekeystone_dump.json')
    products = filter_scraped(products, scraped)

    try:
        for result in crawl_products(products):
            scraped.append(result)
            dump_data('amazon.json', scraped)
            pretty(result) # Nope

    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()

