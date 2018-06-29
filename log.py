import requests as rq
from bs4 import BeautifulSoup as bs
from selenium import webdriver
import re

import config

LOGIN_URL = "http://wwwsc.ekeystone.com/Login"
LOGOUT_URL = "http://wwwsc.ekeystone.com/login?Logout=true"

def set_cookie(resp,s):
	match = re.search(r'ASP.NET_SessionId=([^;]*)',resp.headers['Set-Cookie'])
	if match: 
		cookie = match.group(1)
		s.cookies.set('ASP.NET_SessionId', cookie, domain='wwwsc.ekeystone.com')
		s.cookies.set('AccessoriesSearchResultsPageSize', "48", domain='wwwsc.ekeystone.com')

def get_input(resp):
	data = {}
	html = resp.text
	soup = bs(html, 'html.parser')
	data['smWeb'] = 'webcontent_0$upLogin|webcontent_0$submit'
	data['__LASTFOCUS'] = ''
	data['__EVENTTARGET'] = ''
	data['__EVENTARGUMENT'] = ''
	data['__VIEWSTATE'] = soup.find(id="__VIEWSTATE")["value"]
	data['__VIEWSTATEGENERATOR'] = soup.find(id="__VIEWSTATEGENERATOR")["value"]
	data['__SCROLLPOSITIONX'] = '0'
	data['__SCROLLPOSITIONY'] = '0'
	data['__EVENTVALIDATION'] = soup.find(id="__EVENTVALIDATION")["value"]
	data['webcontent_0$txtUserName'] = config.KEYSTONE_USER
	data['webcontent_0$txtPassword'] = config.KEYSTONE_PASS
	data['__ASYNCPOST'] = 'true'
	data['webcontent_0$submit'] = 'Login'
	return data

def login():
	headers = {
		'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36',
		'accept-language': 'en'
	}
	s = rq.session()
	resp = s.get(LOGIN_URL,headers=headers)
	set_cookie(resp,s)
	data = get_input(resp)
	s.post(LOGIN_URL, data=data,headers=headers)
	return s

def logout(s):
	s.get(LOGOUT_URL)

