#!/usr/bin/env python3

import json
import glob
import sys
import os
import multiprocessing as mp
from bs4 import BeautifulSoup

def product_details(html):

    soup = BeautifulSoup(html, 'html.parser')
    details = soup.select('div.productAttribute')
    result = {}

    for detail in details:
        spans = detail.find_all('span')
        if len(spans) != 2:
            print('Not enough values for dict')
        else:
            name, value = (span.text for span in detail.select('span'))
            result[name] = value

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

def procress_product(filename):
    try:
        html = read_html(filename)
        data = product_details(html)
    except KeyboardInterrupt:
        data = {}
    return data

def process_batch(data):
    with mp.Pool(8) as p:
        yield from p.imap_unordered(procress_product, data)

def main():

    if len(sys.argv) < 2:
        print('Usage: ./decode.py [FILENAME]')
        return

    files = sys.argv[1:]
    results = []

    try:
        for p in process_batch(files):
            results.append(p)
            print(p)

    except KeyboardInterrupt: pass
    finally:
        dump_dict('product_details.json', results)

if __name__ == '__main__':
    main()

