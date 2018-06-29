#!/usr/bin/env python3

import os

# Bullshit
KEYSTONE_USER = os.getenv('KEYSTONE_USER')
KEYSTONE_PASS = os.getenv('KEYSTONE_PASS')

# Shopify
SHOPIFY_SHOP_NAME = os.getenv('SHOPIFY_SHOP_NAME')
SHOPIFY_API_KEY   = os.getenv('SHOPIFY_API_KEY')
SHOPIFY_PASSWORD  = os.getenv('SHOPIFY_PASSWORD')

def main():
    print(KEYSTONE_USER)
    print(KEYSTONE_PASS)
    print(SHOPIFY_SHOP_NAME)
    print(SHOPIFY_API_KEY)
    print(SHOPIFY_PASSWORD)

if __name__ == '__main__':
    main()

