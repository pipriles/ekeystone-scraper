import json
import requests as rq
from bs4 import BeautifulSoup

url = "https://postcalc.usps.com/Calculator/GetMailServices"
HEADERS = { 
    'accept-language': 'en', 
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36', 
}

PRODUCTS = 0

def fill_params(origin_Z, destiny_Z, date, hour, pounds, ounzes, length = 0, height = 0, width = 0):
	params = {}
	params['countryID'] = '0'
	params['countryCode'] = 'US'
	params['origin'] = origin_Z
	params['isOrigMil'] = 'False'
	params['destination'] = destiny_Z
	params['isDestMil'] = 'False'
	params['shippingDate'] = date 
	params['shippingTime'] = hour
	params['itemValue'] = ''
	params['dayOldPoultry'] = 'False'
	params['groundTransportation'] = 'False'
	params['hazmat'] = 'False'
	params['liveAnimals'] = 'False'
	params['nonnegotiableDocument'] = 'False'
	params['mailShapeAndSize'] = 'Package'
	params['pounds'] = pounds
	params['ounces'] = ounzes
	params['length'] = length
	params['height'] = height
	params['width'] = width
	params['girth'] = '0'
	params['shape'] = 'Rectangular'
	params['nonmachinable'] = 'False'
	params['isEmbedded'] = 'False'
	return params

def get_page(params):
	global PRODUCTS
	res = rq.get(url, params=params, headers=HEADERS)
	if res.ok:
		dictionary = json.loads(res.text)
		services = dictionary.get('Page').get('MailServices')
		servicess = []
		for service in services:
			service['Product'] = PRODUCTS 
			servicess.append(service)
		PRODUCTS += 1
		return servicess

def main():
	params = fill_params('18643', '99501', '7/31/2018 12:00:00 AM', '16:29', '1', '1', length = 11, height = 10, width = 5)
	services = get_page(params) #variar product
	with open('services.json', 'w') as f:
		json.dump(services, f, indent=4)


if __name__ == "__main__":
	main()


