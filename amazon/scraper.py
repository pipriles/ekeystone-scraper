#!/usr/bin/env python3

import requests as rq
import json
import pandas as pd
from bs4 import BeautifulSoup
from pathlib import Path
import sys

def pretty(uggly):
    print(json.dumps(uggly, indent=2))

def querify(string):
    return '+'.join(string.split())

def format_search_string_to_url(search_string):
    return 'https://www.amazon.com/s/field-keywords={}'.format(querify(search_string))

def process_tables(tables, keywords):
    caseless_keywords = {s.casefold() for s in keywords} #ensuring all comparisons are caseless
    result = {}
    for table in tables:
        for child in table.children:
            if child.name == 'tr':
                head = child.th.text.strip().casefold()
                data = child.td.text.strip()
                if keywords == []:
                    result[head] = data 
                elif head in caseless_keywords:
                    result[head] = data
    return result	

# select keywords from a product details tables, the search is case insensitive, if ther is some uppercase keywords, they'll be transformed to lowercase
def from_select(product_url, keywords=[]): 

    headers = { 'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36' }
    caseless_keywords = {s.casefold() for s in keywords}
    res = rq.get(product_url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    prod_details = soup.find('div', id='prodDetails')
    det_bullets = soup.find(id='detail-bullets')
    unscrapable = False

    result = {}
    if prod_details:
        tables = prod_details.find_all('table')
        result = process_tables(tables, caseless_keywords)
    elif det_bullets:
        details = det_bullets.select('div.content > ul > li')
        det_list_list = (li.text.split(':', 1) for li in details)
        det_tuples = ((k.strip().casefold(), v.strip()) for k,v in det_list_list)
        result = {k: v for k,v in det_tuples if k in caseless_keywords}
    else:
        print("couldn't find product details table nor details list in product_url: ", product_url)
        unscrapable = True
    
    found_keywords = set(result.keys())
    all_data = True if keywords == [] else found_keywords == caseless_keywords
    some_data = True if keywords == [] else found_keywords != set()

    result['all_details_extracted'] = all_data
    result['some_details_extracted'] = some_data
    result['product_url'] = product_url
    result['unscrapable'] = unscrapable #if this boolean is True, that means that the product was found on amazon but i couldn't scrape the details from it

    return result

def get_product_results(search_string):
    # request
    headers = { 'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36' }
    res = rq.get(format_search_string_to_url(search_string), headers=headers)
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
    if not results:
        return { 'found': False }
    extracted_data = from_select(results[0]['url'], details)
    return { **extracted_data, 'found': extracted_data['some_details_extracted'] }

def build_queries_from_product(product):
    brand = product['supplier']
    subcategory = product['subcategory'].strip()
    number = product['num'][0: product['num'].find('(')].strip()
    yield '{} {}'.format(subcategory, number)
    yield '{} {}'.format(brand, number)

#search products info, optional, just search some details from products (details = list of keywords of details. example: ['shipping weight', 'product dimensions'])
def search_products(product_list, details=[]):
    for product in product_list:
        result = {}
        search_strings = []
        exceptions = []
        for search_string in build_queries_from_product(product):
            search_strings.append(search_string)
            try:
                result = search_product_info(search_string, details)

            except Exception as e:
                exceptions.append(str(e))
                result['found'] = False

            if result['found']: 
                break

        result['exceptions'] = exceptions

        if result['found']:
            yield { 
                'pid': product['pid'],
                'query_strings': search_strings,
                **result
            }

# Make a list of products that haven't been scraped

def filter_out_scraped_products(products, scraped_producs):
    products_left = []
    for product in products:
        if product['pid'] not in (p['pid'] for p in scraped_producs):
            products_left.append(product)
    return products_left

def create_if_not_exists(path, init_data):
    try:
        path.resolve(strict = True)
    except FileNotFoundError:
        path.open('w').write(init_data)
    finally:
        return None

def main():
    product_list = []
    productdf = pd.DataFrame()
    scraped_products = []
    failed_products = []
    path = Path('.')
    cols = {
        'product dimensions': [],
        'shipping Weight': [],
        'found': [],
        'pid': [],
        'query_string': []
    }

    if len(sys.argv) < 2:
        print('to call this program run: python scriptName.py csvFileName.csv')
        return None

    #with open(sys.argv[1], 'r', encoding='utf-8') as ifile:
    #	product_list = json.load(ifile)

    with open(sys.argv[1], 'r', encoding='utf-8') as ifile:
        productdf = pd.read_csv(ifile)

    productdf.columns = [c.casefold() for c in productdf.columns]
    product_list = list(productdf.T.to_dict().values())

    if not product_list:
        print('Error: no products file to scrape')
        return None

    init_data = pd.DataFrame(cols).to_csv()
    create_if_not_exists(path/'dumpeo_1.csv', init_data) # init file for already scraped products
    create_if_not_exists(path/'faileo_1.csv', init_data) # init file for failed to scrape products

    with open('dumpeo_1.csv', 'r', encoding = 'utf-8') as scraped_file:
        scraped_products = list(pd.read_csv(scraped_file).T.to_dict().values())

    with open('faileo_1.csv', 'r', encoding='utf-8') as failed_file:
        failed_products = list(pd.read_csv(failed_file).T.to_dict().values())

    for result in search_products(filter_out_scraped_products(product_list, scraped_products), ['shipping weight', 'product dimensions']):
        if result['found']:
            scraped_products.append(result)	
            with open('dumpeo_1.csv', 'w', encoding='utf-8') as ofile:
                ofile.write(pd.DataFrame(scraped_products).to_csv())
        else:
            failed_products.append(result)
            with open('faileo_1.csv', 'w', encoding='utf-8') as ofile:
                ofile.write(pd.DataFrame(failed_products).to_csv())
        pretty(result)

if __name__ == '__main__':
    main()

