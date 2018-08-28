#!/usr/bin/env python3

import json
import glob
import sys
import re
import os
import multiprocessing as mp
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

OUTPUT_FILE = './dumps/product_details.json'

def product_details(html):

    soup = BeautifulSoup(html, 'html.parser')
    details = soup.select('div.productAttribute')
    result = {}

    for detail in details:
        spans = detail.find_all('span')
        if len(spans) != 2:
            print('Not enough values for dict')
            continue
        name, value = (span.text for span in detail.select('span'))
        result[name] = value

    return result

def product_data(html):

    nonalpha = re.compile(r'\W+')
    soup = BeautifulSoup(html, 'html.parser')
    result = {}

    def extract_detail_text(*args, **kwargs):
        elem = soup.find(*args, **kwargs)
        if elem is None: return
        text = elem.get_text()
        text = re.sub(r'[^\x00-\x7f]', r' ', text)
        text = text.strip()
        return text

    def extract_media_src(img):
        src = img.get('src')
        src = re.sub(r'\&.+$', r'', src) if src else None
        return src

    def extract_body_html(body):
        related = body.find(class_='relatedProducts')
        if related: related.decompose()
        processing = body.find_all(class_='devPartialProcessing')
        for p in processing: p.decompose()
        return body.prettify()

    def extract_table_dict(table):

        rows = table.select('tr')
        data = {}

        for row in rows:
            cols = row.select('td')
            if len(cols) < 2: continue
            key, val = cols[:2]
            key = key.get_text().strip()
            key = nonalpha.sub(r'', key)
            val = val.get_text().strip()
            val = nonalpha.sub(r'', val)
            data[key] = val

        return data

    # New features
    # Supplier vendor
    id_ = 'webcontent_0_row2_0_productDetailBasicInfo_aSupplier'
    text = extract_detail_text(id=id_)
    result['supplier'] = text
    print('Vendor:', text)

    text = extract_detail_text(class_='partHeader')
    result['title'] = text
    print('Title:', text)

    text = extract_detail_text(class_='partDescription')
    result['description'] = text
    print('Description:', text)

    id_ = 'webcontent_0_row2_0_productDetailBasicInfo_lblPartNumber'
    text = extract_detail_text(id=id_)
    result['mfr_part'] = text
    print('MFR Part:', text)

    id_  = 'webcontent_0_row2_0_productDetailBasic'
    id_ += 'Info_lblSecondaryPartId'
    text = extract_detail_text(id=id_)
    result['keystone_part'] = text
    print('Keystone Part:', text)

    id_ = 'webcontent_0_row2_0_productDetailBasicInfo_lblRetailPrice'
    text = extract_detail_text(id=id_)
    result['retail_price'] = text
    print('Retail Price:', text)

    id_ = 'webcontent_0_row2_0_productDetailBasicInfo_lblJobberPrice'
    text = extract_detail_text(id=id_)
    result['jobber_price'] = text
    print('Jobber Price:', text)

    id_ = 'webcontent_0_row2_0_productDetailBasicInfo_lblMyPrice'
    text = extract_detail_text(id=id_)
    result['my_price'] = text
    print('My Price:', text)

    text = extract_detail_text(class_='inventoryLink')
    result['inventory'] = text
    print('Stock:', text)
    
    imgs = soup.select('#partImage img')
    src = { extract_media_src(img) for img in imgs }
    result['images'] = list(src)
    print('ImageUrl:', src)

    bodies = soup.find_all(class_='PartTabBody')
    htmls = [ extract_body_html(body) for body in bodies ]
    result['body_html'] = htmls

    table = soup.find('table', class_='tblInventoryDetail')
    stock = extract_table_dict(table)
    result['inventory_details'] = stock

    # 'title': title
    # 'pid', pid
    # 'images', images
    # 'body_html', body_html[0]
    # 'price': price, 
    # 'inventory': stock	
    # Impossibul
    # Width Length Height

    # print(result)
    print('--------------------')

    return result

def read_html(filename):

    try:
        data = None
        with open(filename, 'r', encoding='utf8') as fl:
            data = fl.read()
    except FileNotFoundError: pass
    return data

def dump_dict(filename, data):
    with open(filename, 'w', encoding='utf8') as fl:
        json.dump(data, fl, indent=2)

def basename(path):
    base = os.path.basename(path)
    name = os.path.splitext(base)[0]
    return name

# Very very ugly
def _match_similar(df, keystone):
    
    regex = re.compile(r'=\"(.+)\"')
    resup = re.compile(r'\((\S+)\)$')
    parts = keystone.PartNumber.apply(lambda x: \
        regex.search(x).group(1))

    for i, row in df.iterrows():
        num     = row.keystone_part
        matches = keystone[parts == num]
        match   = pd.Series(name=row.name)
        for j, m in matches.iterrows():
            code = resup.search(row.supplier).group(1)
            if m.VenCode == code:
                match = m
                break
        match.name = row.name
        yield match

def procress_product(filename):
    try:
        # Assume filename has pid...
        # If it doesn't, it won't work
        name = re.search(r'product_(.+).html', filename)
        html = read_html(filename)
        data = product_data(html)
        data['pid'] = name.group(1)
        print(data.keys())
    except KeyboardInterrupt:
        data = {}
    return data

def process_batch(data, N=4):
    with mp.Pool(N) as p:
        yield from p.imap(procress_product, data)

def main():

    if len(sys.argv) < 2:
        print('Usage: ./decode.py [FILENAME]')
        return

    files = sys.argv[1:]
    results = []

    try:
        for p in process_batch(files):
            results.append(p)

    except KeyboardInterrupt: pass
    finally:
        dump_dict(OUTPUT_FILE, results)

if __name__ == '__main__':
    main()

