#!/usr/bin/env python3

import shopify
import config
import re
import json
import sys
import random
import pandas as pd

# We should add to scraper:
# - Subcategory and category
# - Looks like we are not scraping the id
# - Name looks like supplier
# - NUM is not actually id
# - What should we use as a title?
# - Description looks like product name
# - We should clean the description to look nice

# Shopify data:
# - https://help.shopify.com/api/reference/products/product
# - https://help.shopify.com/api/reference/products/product_variant
# - The rest of the data should be manual
# [x] Title
# [x] Body html (Description by default)
# [x] Vendor (Supplier?)
# [-] Product Type (Subcategory?)
# [x] Published: false
# [x] Price
# [-] Variants (Sort of)
# [ ] Options
# [ ] Tags (Maybe generating them)
# [ ] Weight (Not Keystone)
# [x] Stock (Not shopify)
# [x] Images
# [ ] Sku (Keystone id?)

SHOP_NAME = config.SHOPIFY_SHOP_NAME
API_KEY   = config.SHOPIFY_API_KEY
PASSWORD  = config.SHOPIFY_PASSWORD
SHOP_URL  = f'https://{API_KEY}:{PASSWORD}@{SHOP_NAME}.myshopify.com/admin'

def prepare_shop():
    shopify.ShopifyResource.set_site(SHOP_URL)

def prepare_product(product):
    price = re.search(r'[\d\.]+', product.get('retail_price'))
    price = float(price.group()) if price else None
    return {
        "title": product.get('title'),
        "body_html": product.get('body_html'),
        "published": False,
        "vendor": product.get('supplier'),
        "product_type": product.get('subcategory'),
        # We don't have this information for now
        # "product_type": 'Cleaning and Polishing',
        # "tags": 'carrand microfiber, microfiber',
        # "images": [ { "src": product.get('img') } ],
        "images": [ { 'src': x } for x in product.get('images') ],
        "variants": [ { "price": price } ]
    }

def add_product(product):
    created = shopify.Product.create(product)
    return created

def find_products(products):
    query = ', '.join(products)
    return shopify.Product.find(ids=query)

def read_dump(filename):
    with open(filename, 'r', encoding='utf8') as fp:
        return json.load(fp)

def write_created(filename, data):
    with open(filename, 'w') as fp:
        json.dump(data, fp, indent=4)

def main():

    if len(sys.argv) != 2:
        print('Usage: ./myshopify.py [FILENAME]')
        return

    filename = sys.argv[1]
    data = read_dump(filename)

    df = pd.DataFrame(data)
    df = df.sample(frac=1)
    df.drop_duplicates(subset='supplier', inplace=True)
    data = df.sample(5).to_dict(orient='records')
    
    # This will change shopify resource state
    # Remember to prepare the shop
    # before performing some requests
    prepare_shop()

    created_products = []
    for p in data:
        prepared = prepare_product(p)
        new = add_product(prepared)
        created_products.append(new)
        print(new)
        
    dump = [ x.to_dict() for x in created_products ]
    write_created('created.json', dump)

if __name__ == '__main__':
    main()

