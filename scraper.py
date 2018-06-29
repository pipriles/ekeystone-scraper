#!/usr/bin/env python3

import config
from selenium import webdriver

def login(driver):

    if config.KEYSTONE_USER is None \
    or config.KEYSTONE_PASS is None:
        raise Exception('Set credentials!')

    driver.get('https://wwwsc.ekeystone.com/login')
    username = driver.find_element_by_id('webcontent_0_txtUserName')
    password = driver.find_element_by_id('webcontent_0_txtPassword')
    username.send_keys(config.KEYSTONE_USER)
    password.send_keys(config.KEYSTONE_PASS)
    submit = driver.find_element_by_id('webcontent_0_submit')
    submit.click()
    return driver.get_cookies()

def scrape_search(driver, query):

    url = 'https://wwwsc.ekeystone.com/Search?browse={}'.format(query)
    driver.get(url)

def main():
    driver = webdriver.Chrome()
    login(driver)

    query = 'sub|Lug+Bolts'
    scrape_search(driver, query)

    input('Wait...')

if __name__ == '__main__':
    main()
