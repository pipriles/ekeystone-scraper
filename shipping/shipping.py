#!/usr/bin/env python3

import json
import requests as rq
from bs4 import BeautifulSoup

url = "https://postcalc.usps.com/Calculator/GetMailServices"
HEADERS = { 
    'accept-language': 'en', 
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36', 
}

def fill_params(origin_Z, destiny_Z, date, hour, pounds, ounzes):
    params = {}
    params['countryID'] = '0'
    params['countryCode'] = 'US'
    params['isOrigMil'] = 'False'
    params['isDestMil'] = 'False'
    params['itemValue'] = ''
    params['dayOldPoultry'] = 'False'
    params['groundTransportation'] = 'False'
    params['hazmat'] = 'False'
    params['liveAnimals'] = 'False'
    params['nonnegotiableDocument'] = 'False'
    params['mailShapeAndSize'] = 'Package'
    params['length'] = '0'
    params['height'] = '0'
    params['width'] = '0'
    params['girth'] = '0'
    params['shape'] = 'Rectangular'
    params['nonmachinable'] = 'False'
    params['isEmbedded'] = 'False'

    params['pounds'] = pounds
    params['ounces'] = ounzes
    params['origin'] = origin_Z
    params['destination'] = destiny_Z
    params['shippingDate'] = date #7/31/2018+12%3A00%3A00+AM
    params['shippingTime'] = hour

    return params

def get_page(params):
    res = rq.get(url, headers=HEADERS)

    print(res.url)

    with open('debug.html', 'w') as fl:
        fl.write(res.text)

    res.raise_for_status()
    print(res.json())

    with open('gola', 'w', encoding='utf8') as f:
        json.dump(dictionary, f, indent=4)

def main():
    params = fill_params('44106', '20770', '7/31/2018+12:00:00+AM', '16:29', '6', '1.44')
    get_page(params)


if __name__ == "__main__":
	main()


