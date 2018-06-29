#!/usr/bin/env python3

from bs4 import BeautifulSoup as bs
from selenium import webdriver
import requests as rq
import json
import log

BASE_URL = "http://wwwsc.ekeystone.com"
HEADERS = { 
    'accept-language': 'en', 
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36', 
}

def get_categories(s):
	categories = []
	resp = s.get(BASE_URL)
	soup = bs(resp.text, 'html.parser')
	menu = soup.select("li.MainMenuItem > a")

	if menu: categories = [(x.get_text(),x['href']) for x in menu]

	return categories

def sub_categories(s,categorie):
	subcategories = []
	resp = s.get(BASE_URL+categorie)
	soup = bs(resp.text, 'html.parser')
	menu = soup.select(".doormatSubCategory")

	if menu: subcategories = [(x.get_text(),x['href']) for x in menu]

	return subcategories

def scrape_products(html):
	scraped_p = []
	soup = bs(html, 'html.parser')
	products = soup.select(".resultsStatic")
	for product in products:
		#PHOTO
		img_tag = product.select_one("img")
		img = img_tag['src'] if img_tag else None
		scraped_p.append({'img': img})
		#NAME & NUMBER
		res_content = product.select_one(".resultsContentHeader")
		name_num = res_content.select("span")
		name = None
		num = None
		if name_num: 
			name = name_num[0].get_text()
			num = name_num[-1].get_text()
		scraped_p[-1]["name"] = name
		scraped_p[-1]["num"] = num
		#DESCRIPTION
		description = product.select_one(".descriptionLink a")
		scraped_p[-1]["description"] = description.get_text() if description else None
		#RESTRICTION
		restriction = product.select_one(".requiredProductsMessage")
		message = restriction.get_text() if restriction else None
		restriction = product.select_one(".restrictionsText img")
		title = restriction['title'] if restriction else None
		scraped_p[-1]["restriction"] = message.strip() if message else title
		#PRICE
		price_span = product.select_one(".resultsPricingArea span span")
		price = price_span.get_text() if price_span else None
		scraped_p[-1]["price"] = price
		#AVAILABILITY
		inventory_div = product.select_one("div.inventoryDiv")
		message = inventory_div.select_one(".inventory a")
		table = inventory_div.select("tr")
		availability = {}
		for x in table:
			name_td = x.select_one(".name")
			av_td = x.select_one(".value")
			name = name_td.get_text() if name_td else None
			av = av_td.get_text() if av_td else None
			if name: availability[name] = av
		if not availability and message:
			availability = message.get_text() +" "
			td = table[0].select_one("td") if table else None
			availability += td.get_text() if td else ""
		scraped_p[-1]["availability"] = availability

	return scraped_p

def start_selenium(s):
	cookie_id = {'domain': 'wwwsc.ekeystone.com', 'name': 'ASP.NET_SessionId', 'value': s.cookies['ASP.NET_SessionId']}
	cookie_items = {'domain': 'wwwsc.ekeystone.com', 'name': 'AccessoriesSearchResultsPageSize', 'value': '48'}
	driver = webdriver.Chrome()
	driver.get(BASE_URL)
	driver.delete_all_cookies()
	driver.add_cookie(cookie_id)
	driver.add_cookie(cookie_items)
	return driver

def wait(driver,html):
	display = True
	soup = bs(html, 'html.parser')
	while display:
		driver.implicitly_wait(5)
		hidden = driver.find_elements_by_css_selector("#webcontent_0_row2_0_upSearchProgress")
		if not hidden[0].is_displayed():
			display = False

def find_next_page(driver):
	nextp = None
	contin = True
	a = driver.find_elements_by_css_selector("div.pageNumbers")
	if a: 
		nextp = a[0].find_elements_by_css_selector("a.activePage + a")
		if not nextp: contin = False
	else:
		contin = False

	return contin,nextp


def paginate(driver):
	products = []
	contin = True
	while contin:
			html = driver.page_source
			result = scrape_products(html)
			products = products + result
			try:
				contin,nextp = find_next_page(driver)
				if nextp: nextp[0].click()
			except:
				pass
			finally:
				wait(driver,driver.page_source)
			
	return products


def scrape_subcat(s,subcat):
	products = []
	driver = start_selenium(s)
	for x in subcat:
		print(x[0])

		driver.get(BASE_URL+x[1])
		result = paginate(driver)
		products = result + products
		with open("dumpeo.json", 'w', encoding='utf8') as f:
			json.dump(products, f, indent=4)

			


def main():
	try:
	    s = log.login()
	    categories = get_categories(s)
	    if categories: 
	    	subcat = sub_categories(s,categories[0][1]) 
	    	if subcat: 
	    		scrape_subcat(s,subcat)
	except KeyboardInterrupt:
		print("Chao Chichobello")
	finally:
		log.logout(s)


if __name__ == '__main__':
    main()