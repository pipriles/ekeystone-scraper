#!/usr/bin/env python3

import requests as rq
import json

from bs4 import BeautifulSoup
from itertools import zip_longest

def pretty(uggly):
    print(json.dumps(uggly, indent=2))

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

def get_product_links(search_string):
    # request
    query = '+'.join(search_string.split())
    url = 'https://www.amazon.com/s/field-keywords={}'.format(query)
    res = rq.get(url)
    # parsing html
    soup = BeautifulSoup(res.text, 'html.parser')
    items = soup.select('div[class*="item-container"]')
    links = []

    for i in items:
        link = i.select_one('a[class*="access-detail-page"]')
        if link is not None:
            links.append(link['href'])

    return links

def first_best_fit():
    pass

def seach_products(product_list):
    result = []
    for search_string in product_list:
        result.append({ search_string: get_product_info() })
    return result	

def main():
    search_string = 'Mouse spectrum logitech'
    for link in get_product_links(search_string):
        pretty(get_product_info(link))

if __name__ == '__main__':
    main()

