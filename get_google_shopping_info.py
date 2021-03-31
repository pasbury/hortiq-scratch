#!/usr/bin/env python
# coding: utf-8

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
import json
import pandas as pd
from collections import defaultdict
import re
import jellyfish as jf
from urllib.parse import urlparse
import string
import argparse
from datetime import date, datetime


options = Options()
options.headless = False
DRIVER_PATH = './chromedriver_win32/chromedriver.exe'


def check_exists_by_xpath(driver, xpath):
    try:
        driver.find_element_by_xpath(xpath)
    except NoSuchElementException:
        return False
    return True


def no_punc(s):
    keep = string.ascii_letters + ' ' + str(u'\u00D7')
    return ''.join([c for c in s if c in keep])


def plant_name_check(plant_name_1, plant_name_2, max_lev_dist=3):
    n1 = no_punc(plant_name_1).lower()
    n2 = no_punc(plant_name_2).lower()

    # First check if names are the same (save some work if we are very lucky!)
    if n1 == n2:
        return 1
    else:
        l1 = n1.split()
        l2 = n2.split()        
        # Check if all of the words in the queries plant name are in the found plant name...
        _1_is_in_2 = 1
        for w in l1:
            if not w in(l2):
                 _1_is_in_2 = 0
        _2_is_in_1 = 1
        # ...and visa versa
        for w in l2:
            if not w in(l1):
                 _2_is_in_1 = 0
        if _1_is_in_2 or _2_is_in_1:
            return 2
        # Get Levenshtein distance
        if jf.levenshtein_distance(n1,n2) <= max_lev_dist:
            return 3
        else:
            return 4


def get_rhs_google_map(driver, rhs_id, botanical_name, common_name):
    
    # Search for plant_name on google shopping
    plant_name_query = '+'.join(no_punc(botanical_name).split())
    url = 'https://www.google.co.uk/search?q=' + plant_name_query + '&tbm=shop'
    driver.get(url)
    print(driver.current_url)
    time.sleep(2)
    
    
    # Handle cookie consent
    if driver.current_url.find('consent') > 0:
        print('Cookie consent')
        agree_button = WebDriverWait(driver,20).until(EC.element_to_be_clickable((By.XPATH,'//button[@class="VfPpkd-LgbsSe VfPpkd-LgbsSe-OWXEXe-k8QpJ VfPpkd-LgbsSe-OWXEXe-dgl2Hf nCP5yc AjY5Oe DuMIQc"]/div[@class="VfPpkd-RLmnJb]')))
        agree_button.click()
        time.sleep(2)
        print(driver.current_url)
    
    
    # Find list of matching search results
    soup = BeautifulSoup(driver.page_source, "html.parser")
    results_html = soup.find("div", {"class": "sh-pr__product-results"})
    if results_html is not None:
        results_list = results_html.find_all("div", {"class": "sh-dlr__list-result"})
        if results_list is not None:
            match_list = []
            [match_list.append(i) for i in results_list if ( ( plant_name_check(botanical_name,i.find("h3", {"class":"xsRiS"}).text) < 4 ) or ( plant_name_check(common_name,i.find("h3", {"class":"xsRiS"}).text) < 4) )]
            #print(len(match_list))

            # Extract data and return as list of dict
            rhs_google_map_list = []
            rhs_google_map = {}
            for p in match_list:
                rhs_google_map = {}        
                rhs_google_map["rhs_id"] = rhs_id
                rhs_google_map["google_id_type"] = "data-docid"
                rhs_google_map["google_id"] = p.get('data-docid')
                #print('made it to here')        
                rhs_google_map["google_product_url"] = 'https://www.google.co.uk/shopping/product/1?prds=pid:' + rhs_google_map["google_id"]
                rhs_google_map["query_date"] = date.today().strftime("%d-%b-%Y")

                rhs_google_map_list.append(rhs_google_map)
                #print(rhs_google_map_list)
        
            return rhs_google_map_list
    else:
        return None


def get_buying_options(driver, url, pid):
    
    # Go to product page and extract info
    driver.get(url)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    
    buying_options_list = []
    buying_options = {}
    
    # product-level
    google_product_title = soup.find("span", {"class":"BvQan sh-t__title-pdp sh-t__title translate-content"}).text
    google_product_desc = soup.find("span", {"class":"sh-ds__trunc-txt translate-content"}).text
    today = date.today().strftime("%d-%b-%Y")
    
    # per buying option
    # first check that the buying options table is present and structured as expected
    if soup.find("table", {"class":"dOwBOc"}) is not None:
        #print("found buying options table")
        headers = soup.find("tr", {"class":"sh-osd__headers"}).find_all("th")
        if headers is not None:
            #print("found " + str(len(headers)) + " items in table headers row" )
            if headers[0].text != "Sold by":
                good = False
            elif headers[1].text != "Details & special offers":
                good = False
            elif headers[2].text != "Item price":
                good = False
            elif headers[3].text != "Total price":
                good = False
            else:
                good = True
            if good:
                #print("table headers as expected")
                body = soup.find("tbody", {"id":"sh-osd__online-sellers-cont"})
                rows = body.find_all("tr",recursive=False)
                num_rows = len(rows)            
                for r in rows:
                    buying_options = {}
                    cells = r.find_all("td",recursive=False)
                    buying_options["merchant_name"] = cells[0].find("a", {"class":"sh-osd__seller-link shntl"}).find("span").text
                    buying_options["details_and_offers"] = cells[1].text
                    buying_options["item_price"] = cells[2].text
                    buying_options["total_price"] = cells[3].find("div", {"class":"sh-osd__total-price"}).text
                    href = cells[0].find("a", {"class":"sh-osd__seller-link shntl"})["href"]
                    driver.get("http://www.google.com" + href)
                    buying_options["merchant_url"] =  driver.current_url
                    buying_options["merchant_netloc"] = urlparse(driver.current_url)[1]
                    buying_options["query_date"] = today
                    buying_options["google_product_title"] = google_product_title
                    buying_options["google_product_desc"] = google_product_desc
                    buying_options["google_id"] = pid
                    buying_options_list.append(buying_options)
            
    else:
        buying_options["merchant_name"] = ""
        buying_options["details_and_offers"] = ""
        buying_options["item_price"] = ""
        buying_options["total_price"] = ""
        buying_options["merchant_url"] =  ""
        buying_options["merchant_netloc"] = ""
        buying_options["query_date"] = today
        buying_options["google_product_title"] = google_product_title
        buying_options["google_product_desc"] = google_product_desc
        buying_options["google_id"] = pid
        buying_options_list.append(buying_options)
        
    return buying_options_list


def main():
    
    help_text = "Script to search for plants on Google shopping and find the online buying options listed there.  Requries input in format output by 'find_plants.py'. Outputs two files, (1) mapping RHS plant id <--> Google shopping product id, and (2) list if 'buying options' with prices.  User may optionally specify output file names."
    parser = argparse.ArgumentParser(description=help_text)
    parser.add_argument("-mf", "--mapfile", help="file path and filename for plant <--> product mapping", type=str)
    parser.add_argument("-bf", "--buyingfile", help="file path and filename for buying options output", type=str)    
    parser.add_argument("infile", help="list of plants output by find_plants.py", type=str)
    args = parser.parse_args()
    
    
    driver = webdriver.Chrome(executable_path=DRIVER_PATH, options=options)

    
    # read file
    infile = args.infile    
    with open(infile, 'r') as infile:
        indata=infile.read()    
    
    # parse file
    plantlist = json.loads(indata)
    n = len(plantlist['data'])
    
    try:
        rhs_google_map = []
        google_buying_options = []
        #with open("testmap.txt", 'w') as fm, open("testbuying.txt", 'w') as fb:
        for i, plant in enumerate(plantlist['data']):
            #time.sleep(5)
            print('Processing plant ' + str(i+1) + ' of ' + str(n) + '.')
            try:
                products = get_rhs_google_map(driver, plant['rhs_id'], plant['botanical_name'], plant['common_name'])
            except Exception as e:
                print('Unable to get google products for plant ' + str(plant['rhs_id']))
                print(e)
            else:
                rhs_google_map.extend(products)
                for product in products:
                    try:
                        buying_options = get_buying_options(driver, product["google_product_url"], product["google_id"])
                    except:
                        print('Unable to get buying options from ' + str(product["google_product_url"]))
                    else:
                        google_buying_options.extend(buying_options)

        
        dfmap = pd.DataFrame(rhs_google_map)
        if args.mapfile is not None:
            mapfilename = args.mapfile
        else:
            mapfilename = 'plant_prod_map_' + datetime.now().strftime("%Y%b%d-%H%M%S") +'.txt'       
        dfmap.to_json(path_or_buf=mapfilename,orient='table',index=False)
        
        dfbuying = pd.DataFrame(google_buying_options)
        if args.buyingfile is not None:
            buyingfilename = args.buyingfile
        else:
            buyingfilename = 'buying_options_' + datetime.now().strftime("%Y%b%d-%H%M%S") +'.txt'          
        dfbuying.to_json(path_or_buf=buyingfilename,orient='table',index=False)
        
        print('Results written to ' + mapfilename + ' and ' + buyingfilename)      
        
    except Exception as e:
        print(e)
    finally:
        driver.quit()

if __name__ == '__main__':
    main()