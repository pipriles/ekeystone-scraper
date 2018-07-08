#!/usr/bin/env python3

import requests as rq
from bs4 import BeautifulSoup
from urllib.parse import urlparse

def powered_by_shopify(url):
    soup = BeautifulSoup(rq.get(url).text, 'html.parser')
    return True if soup.select_one('[id*="shopify"]') else False

def shop_links(href):
    return href and ('shop' in href or 'store' in href)
	
# url candidate list to find the domain's shopify
def url_candidates(url):
    yield url 		# try with the original domain
    # else, find potential shop links in the domain
    soup = BeautifulSoup(rq.get(url).text, 'html.parser')
    candidates = soup.find_all(href=shop_links)
    for tag in candidates:
        yield tag['href']
    # else, do some desperate tries
    parsed = urlparse(url)
    yield '{}://shop.{}'.format(parsed.scheme, parsed.netloc) 
    yield '{}://{}.myshopify.com'.format(
            parsed.scheme, parsed.netloc.split('.', 1)[0])
    # only god can help you now

def shop(url):
    for url in url_candidates(url):
        if powered_by_shopify(url):
            return url
    else:
        None

def main():
    url = input('insert the domain url: ')
    print('the shop is: ', shop(url))

if __name__ == '__main__':
	main()
