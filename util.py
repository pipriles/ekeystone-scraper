#!/usr/bin/env python

import time
import re
import numbers
import json
import config

DEFAULT_STATUS = { 'status': None, 'pending': 0, 
        'price_rate': config.PRICE_RATE, 'target': None }

def parse_price(price):

    if isinstance(price, numbers.Number):
        return price

    clean = re.sub(r'[^\d\.]', '', price)
    match = re.search(r'\d*\.?\d*', clean)
    parsed = match.group()

    return float(parsed) if parsed else None

def safe_mode(func):
    def wrapper(*args, **kwargs):
        ret = []
        retries = 1 # Number of attempts
        while retries > 0:
            try:
                ret = func(*args, **kwargs)
                retries = 0
            except Exception as e:
                print(e)
                retries -= 1
                time.sleep(3)
            return ret
    return wrapper

def read_json(filename, default=None, *args, **kwargs):
    try:
        data = default
        with open(filename, 'r', encoding='utf8') as fp:
            data = json.load(fp, *args, **kwargs)
    except Exception: pass
    return data

def write_json(filename, data, *args, **kwargs):
    with open(filename, 'w', encoding='utf8') as fp:
        json.dump(data, fp, *args, **kwargs)

def write_status(st):
    current = read_json(config.STAT_FILE, default={})
    current.update(st)
    write_json(config.STAT_FILE, current)
    return current

def read_status(override={}):
    st = read_json(config.STAT_FILE, default={})
    default = DEFAULT_STATUS.copy()
    default.update(st)
    default.update(override)
    return default

