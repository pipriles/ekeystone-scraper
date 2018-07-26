import multiprocessing as mp
import functools
import shipping
import json
import re

def crawl_products(products, N=4):
	scraped = []
	for product in products:
		params = shipping.fill_params(94016,10001,'7/31/2018 12:00:00 AM','16:29',product.get('pounds'),product.get('ounzes'),length = product.get('length'), height = product.get('height'), width = product.get('width'))
		scraped.append(shipping.get_page(params))
	return scraped

def process_products(products):
	hey = []
	for product in products:
		length = 0
		height = 0
		width = 0
		ounzes = 0
		pounds = 0
		if product.get('found'):
			if not product.get('unscrapable'):
				hey.append({})
				hey[-1]['PID'] = product.get('pid')
				dimensions = product.get('product dimensions')
				if dimensions: match = re.search(r'([0-9]*) x ([0-9]*) x ([0-9]*)',dimensions)
				if match:
					length = match.group(1)
					height = match.group(2)
					width = match.group(3)
				weight = product.get('shipping weight')
				if weight: match1 = re.search(r'([0-9]*\.?[0-9]*) (\w)',weight)	
				if match1:
					typ = match1.group(2)
					if typ == 'o':
						ounzes = match1.group(1)
					else:
						pounds = match1.group(1)
				hey[-1]['length'] = length
				hey[-1]['height'] = height
				hey[-1]['width'] = width
				hey[-1]['ounzes'] = ounzes
				hey[-1]['pounds'] = pounds
	return hey

def main():
	scraped = []
	with open("amazon.json","r") as f:
		products = json.load(f)
	products = process_products(products)
	scraped = crawl_products(products)
	with open('services.json', 'w') as f:
		json.dump(services, f, indent=4)

if __name__ == "__main__":
	try:
		main()
	except KeyboardInterrupt:
		pass
