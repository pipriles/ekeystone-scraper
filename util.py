#!/usr/bin/env python

import time
import re
import numbers

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

