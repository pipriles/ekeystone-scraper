#!/usr/bin/env python3

import shopify
import config
import re
import json

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
# [-] Vendor (Supplier?)
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

SHOP_URL  = 'https://{}:{}@{}.myshopify.com/admin'
SHOP_URL  = SHOP_URL.format(API_KEY, PASSWORD, SHOP_NAME)

def prepare_shop():
    shopify.ShopifyResource.set_site(SHOP_URL)

def prepare_product(product):
    price = re.search(r'[\d\.]+', product.get('price'))
    price = float(price.group()) if price else None
    return {
        "title": product.get('num'),
        "body_html": product.get('description'),
        "published": False,
        # We don't have this information for now
        # "vendor": "Burton",
        # "product_type": 'Cleaning and Polishing',
        # "tags": 'carrand microfiber, microfiber',
        "images": [ { "src": product.get('img') } ],
        "variants": [ { "price": price }]
    }

def add_product(product):
    created = shopify.Product.create(product)
    return created

def find_products(products):
    query = ', '.join(products)
    return shopify.Product.find(ids=query)

def read_dump(filename):
    with open('./dumpeo.json', 'r', encoding='utf8') as f:
        return json.load(f)

def write_created(filename, data):
    with open(filename, 'w') as c:
        json.dump(data, c, indent=4)

def main():

    data = read_dump('./dumpeo.json')

    # This will change shopify resource state
    # Remember to prepare the shop
    # before performing some requests
    prepare_shop()

    created_products = []
    for p in data[:3]:
        prepared = prepare_product(p)
        new = add_product(prepared)
        created_products.append(new)
        print(new)
        
    dump = [ x.to_dict() for x in created_products ]
    write_created('created.json', dump)

if __name__ == '__main__':
    main()

