#!/usr/bin/env python3

import shopify
import config
import re
import json
import sys
import random
import time
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

# This function needs weight
def prepare_product(product):
    price = re.search(r'[\d\.]+', product.get('retail_price'))
    price = float(price.group()) if price else None

    stock = product['inventory_details'].values()
    count = sum(map(int, stock))

    return {
        "title": '{} / {}'.format(
                product.get('title'),
                product.get('description')
            ),
        "body_html": product.get('body_html'),
        "published": False,
        "vendor": product.get('supplier'),
        "product_type": product.get('subcategory'),
        # We don't have this information for now
        # "tags": 'carrand microfiber, microfiber',
        "weight": product.get('Weight'),
        "images": [ { 'src': x } for x in product.get('images') ],
        "variants": [ { 
            "price": price,
            "inventory_quantity": count 
        } ]
    }

def fetch_all_products(**kwargs):

    count = shopify.Product.count(**kwargs)
    limit = 250
    pages = count // limit

    for p in range(1, count // limit + 2):
        print(p, 'Fetching products...')
        yield from shopify.Product.find(
                limit=limit, page=p, **kwargs)

def retry_on_error(func):
    def wrapper(*args, **kwargs):
        ret = None
        retries = 2 # Number of attempts
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

@retry_on_error
def add_product(product):
    created = shopify.Product.create(product)
    return created

@retry_on_error
def update_product(data):

	id_ = data['shopify_id']
	print('Updating shopify product', id_)

	product = shopify.Product.find(id_)
	stock = data['inventory_details'].values()
	count = sum(map(int, stock))

	for p in product.variants:
        # Update variant properties...
        # p.price = data['retail_price']
		
		# This is depreacted
		p.inventory_management = 'shopify'
		p.inventory_quantity = count

	# Commit changes
	product.save()

def find_products(products):
    query = ', '.join(products)
    return shopify.Product.find(ids=query)

def read_dump(filename):
    with open(filename, 'r', encoding='utf8') as fp:
        return json.load(fp)

def write_created(filename, data):
    with open(filename, 'w') as fp:
        json.dump(data, fp, indent=4)

def prepare_frame(products):

    for p in products:
        row = _product_row(p)
        for img in p.get('images', []):
            row['Image Src'] = img
            yield row
            row = { 'Handle': p['title'] }

def _product_row(product):

    price = re.search(r'[\d\.]+', product.get('retail_price'))
    price = float(price.group()) if price else None
    grams = 453.59237 # Grams / lbs rate

    stock = product['inventory_details'].values()
    count = sum(map(int, stock))

    # Title must be less than 255
    # Inventory must be integer

    return {
        'Handle': product['title'],
        'Title': '{} / {}'.format( 
            product.get('title'), 
            product.get('description')
        ),
        'Body (HTML)': product.get('body_html'),
        'Vendor': product.get('supplier'),
        'Type': product.get('subcategory'),
        # 'Tags': Generate them...
        'Published': True, # Set to True
        'Option1 Name': 'Title',
        'Option1 Value': 'Default Title',
        # 'Variant SKU': Should be keystone part
        'Variant Grams': product.get('Weight') * grams,
        'Variant Inventory Qty': str(count),
        'Variant Inventory Policy': 'deny',
        'Variant Fulfillment Service': 'manual',
        'Variant Price': price,
        'Variant Requires Shipping': True,
        # Iterate for each image
        # 'Image Src':  ,
        # 'Variant Image',
        'Variant Weight Unit': 'lb'
    }

def to_handler(title):
    handler = title.lower()
    handler = re.sub(r'\W', ' ', handler)
    chunks  = handler.split()
    return '-'.join(chunks)

# This function may take some time because it first
# fetches all the products from the shopify store
def pids_from_shopify(filename):

    data = read_dump(filename)

    products = fetch_all_products()
    products = pd.Series([ p.handle for p in products ])

    mapper = { to_handler(x['title']): x['pid'] for x in data }
    uploaded = products.map(mapper)
    uploaded.name = 'Pid'

    return uploaded

def main():

    if len(sys.argv) != 2:
        print('Usage: ./myshopify.py [FILENAME]')
        return

    filename = sys.argv[1]
    data = read_dump(filename)
    length = len(data)

    # df = pd.DataFrame(data)
    # df = df.sample(frac=1)
    # df.drop_duplicates(subset='supplier', inplace=True)
    # data = df.sample(5).to_dict(orient='records')
    
    # This will change shopify resource state
    # Remember to prepare the shop
    # before performing some requests
    prepare_shop()

    created = []
    for i, p in enumerate(data[:1], 1):

        prepared = prepare_product(p)
        new = add_product(prepared)

        uploaded = ( p.get('pid'), new.id if new else None )
        created.append(uploaded)

        print(f'{i}/{length} - {new}')
        
    # dump = [ x.to_dict() for x in created ]
    # write_created('created.json', dump)

    write_created('created.json', created)

if __name__ == '__main__':
    main()

