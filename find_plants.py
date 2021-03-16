#!/usr/bin/env python
# coding: utf-8

# # Script to scrape RHS 'Find a Plant' data


import requests
from bs4 import BeautifulSoup
from selenium import webdriver
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from datetime import date, datetime
import json
import pandas as pd
import argparse


def check_exists_by_xpath(driver, xpath):
    try:
        driver.find_element_by_xpath(xpath)
    except NoSuchElementException:
        return False
    return True


def run_query(driver,query='camellia&isAgm=true'):
    
    # Run query
    driver.get('https://www.rhs.org.uk/plants/search-results-beta?query=' + query)
    
    # Print results
    print('Title of webpage is: ' + str(driver.title))
    print('URL of webpage is: ' + str(driver.current_url))
    
    print('Negotiating beta opt-in and model pop-up')
    # Handle model pop-up and beta sign-in
    if driver.current_url.find('beta-optin') > 0:
        optin_button = WebDriverWait(driver,20).until(EC.element_to_be_clickable((By.XPATH,'//button[@class="button button--ghost button--small button--w-100 button--w-auto-sm u-m-y-0"]/span[@class="button__text"][text()="Try the new version"]')))
        if check_exists_by_xpath(driver,'//span[@id="popupCloseTH"]'):
            close_button = driver.find_element_by_xpath('//span[@id="popupCloseTH"]')
            if close_button.is_displayed():
                close_button.click() 
        optin_button.click()
    
    # Print results
    print('Title of webpage is: ' + str(driver.title))
    print('URL of webpage is: ' + str(driver.current_url))
    
    # Simulate scrolling down to bottom of the page to display all results
    print('Starting to scroll through search results')   
    time.sleep(2)
    scroll_pause_time = 1
    screen_height = driver.execute_script("return window.screen.height;")   # get the screen height of the web
    i = 1

    while True:
        # scroll one screen height each time
        driver.execute_script("window.scrollTo(0, {screen_height}*{i});".format(screen_height=screen_height, i=i))  
        i += 1
        time.sleep(scroll_pause_time)
        # update scroll height each time after scrolled, as the scroll height can change after we scrolled the page
        scroll_height = driver.execute_script("return document.body.scrollHeight;")  
        # Break the loop when the height we need to scroll to is larger than the total scroll height
        if (screen_height) * i > scroll_height:
            break 

    print('Finished scrolling through search results')
    
    soup = BeautifulSoup(driver.page_source, "html.parser")
    
    return soup.find("ul", {"class": "gl-view js-gl-view"})
    

def extract_data(plant_list):
    
    plant_list = plant_list.find_all("app-plants-search-list-item", {"class": "gl-view__item"})
    print('The length of the list of search results is: ' + str(len(plant_list)))
    
    today = date.today().strftime("%d-%b-%Y")
    
    from collections import defaultdict
    plants = defaultdict(dict)

    for i, p in enumerate(plant_list):
        plant_title_elements = p.find("div", {"class": "gl-view__content__item-1"})
        plants[i]['img_src'] = p.find("img", {"class": "gl-view__image"})['src']
        plants[i]['botanical_name'] = plant_title_elements.find("h4", {"class": "gl-view__title u-m-b-0"}).text
        plants[i]['common_name'] = plant_title_elements.find("h4", {"class": "gl-view__title text-normal"}).text
        plants[i]['brief_desc'] = p.find("div", {"class": "gl-view__content__item-2"}).find("p").text
        plants[i]['detail_page'] = p.find("a", {"class": "u-faux-block-link__overlay"})['href']
        plants[i]['rhs_id'] = plants[i]['detail_page'].split('/')[2]
        plants[i]['query_date'] = today
        if p.find("i", {"title":"AGM plant"}) is None:
            plants[i]['agm_plant'] = 0
        else:
            plants[i]['agm_plant'] = 1
        supplier_search_elements = p.find("div", {"class": "gl-view__content__item-3"}).findChildren('a')

        if len(supplier_search_elements) == 1:
            plants[i]['num_suppliers'] = supplier_search_elements[0].find("span").text.split()[0]
            plants[i]['supplier_search'] = supplier_search_elements[0]['href']
            plants[i]['rhsplants_url'] = ''
            plants[i]['rhsplants_price_gbp'] = ''        

        elif len(supplier_search_elements) == 2:
            plants[i]['num_suppliers'] = supplier_search_elements[1].find("span").text.split()[0]
            plants[i]['supplier_search'] = supplier_search_elements[1]['href']
            plants[i]['rhsplants_url'] = supplier_search_elements[0]['href']
            plants[i]['rhsplants_price_gbp'] = supplier_search_elements[0].find("span").text.split('£')[1]
        else:
            plants[i]['num_suppliers'] = '0'
            plants[i]['supplier_search'] = ''
            plants[i]['rhsplants_url'] = ''
            plants[i]['rhsplants_price_gbp'] = ''  
    
    print('Extracted ' + str(i+1) + ' rows of data from query results')
    return plants
    

def main():
    
    #arguments = sys.argv[1:]
    #short_option = "o:"
    #long_option = "output="
    
    help_text = "Script to scrape list of plants from RHS Find a plant.  User should supply query string to append to URL after 'https://www.rhs.org.uk/plants/search-results-beta?query=' and also an optional output file."
    parser = argparse.ArgumentParser(description=help_text)
    parser.add_argument("-o", "--outfile", help="output file path and filename", type=str)
    parser.add_argument("query", help="query string to complete URL", type=str)
    args = parser.parse_args()
    
    # Set selenium options
    options = Options()
    options.headless = True
    DRIVER_PATH = './chromedriver_win32/chromedriver.exe'
    driver = webdriver.Chrome(executable_path=DRIVER_PATH, options=options)
    
    try:
        # Run query
        results_html = run_query(driver,args.query)

        # Parse results and convert to json table
        plants = extract_data(results_html)
        dfplants = pd.DataFrame.from_dict(plants, orient='index', dtype='str')
        if args.outfile is not None:
            outfilename = args.outfile
        else:
            outfilename = 'plants_' + datetime.now().strftime("%Y%b%d-%H%M%S") +'.txt'
        dfplants.to_json(path_or_buf=outfilename,orient='table',index=False)

        print('Results written to ' + outfilename)
        
    except:
        print("Something went wrong!")
        
    finally:
        driver.quit()

if __name__ == '__main__':
    main()