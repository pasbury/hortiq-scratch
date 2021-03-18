#!/usr/bin/env python
# coding: utf-8

# # Script to scrape additional info from individual plant page on RHS 'Find a Plant'


import requests
from bs4 import BeautifulSoup
from selenium import webdriver
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from datetime import date
import json
import pandas as pd
from collections import defaultdict
import re
import argparse
from datetime import date, datetime


options = Options()
options.headless = True
DRIVER_PATH = './chromedriver_win32/chromedriver.exe'


def main():
    
    help_text = "Script to enrich list of plants with data from their individual detail pages.  User should supply input file which must be in the format output by 'find_plants.py'.  Optionally, the output file may be specified."
    parser = argparse.ArgumentParser(description=help_text)
    parser.add_argument("-o", "--outfile", help="output file path and filename", type=str)
    parser.add_argument("infile", help="list of plants output by find_plants.py", type=str)
    args = parser.parse_args()
    
    
    driver = webdriver.Chrome(executable_path=DRIVER_PATH, options=options)

    # read file
    infile = args.infile    
    with open(infile, 'r') as infile:
        indata=infile.read()

    # parse file
    plantlist = json.loads(indata)
    updatedplantlist = []
    n = len(plantlist['data'])
    
    for i,d in enumerate(plantlist['data']):
        driver.get('https://www.rhs.org.uk' + d['detail_page'])
            
        # Handle model pop-up and beta sign-in
        if driver.current_url.find('beta-optin') > 0:
            print('Opt-in')
            optin_button = WebDriverWait(driver,20).until(EC.element_to_be_clickable((By.XPATH,'//button[@class="button button--ghost button--small button--w-100 button--w-auto-sm u-m-y-0"]/span[@class="button__text"][text()="Try the new version"]')))
            if check_exists_by_xpath(driver,'//span[@id="popupCloseTH"]'):
                close_button = driver.find_element_by_xpath('//span[@id="popupCloseTH"]')
                if close_button.is_displayed():
                    close_button.click() 
            optin_button.click()

        print('Processing plant ' + str(i+1) + ' of ' + str(n) + '. URL of webpage is: ' + str(driver.current_url))
        time.sleep(3)    
        soup = BeautifulSoup(driver.page_source, "html.parser")
        d.update(get_plant_details(soup))
        updatedplantlist.append(d)
            
    driver.quit()    
    
    dfplants = pd.DataFrame(updatedplantlist)
    if args.outfile is not None:
        outfilename = args.outfile
    else:
        outfilename = 'plants_enriched_' + datetime.now().strftime("%Y%b%d-%H%M%S") +'.txt'
    dfplants.to_json(path_or_buf=outfilename,orient='table',index=False)
        
    print('Results written to ' + outfilename)
    

def check_exists_by_xpath(driver, xpath):
    try:
        driver.find_element_by_xpath(xpath)
    except NoSuchElementException:
        return False
    return True



def find_size(soup, string):
    result = soup.find(string=string)
    if result is None:
        return ''
    else:
        return result.parent.parent.text.split(string)[1].rstrip().lstrip()



def get_plant_details(soup):
# Get additional details for individual plant

    plantinfo = {}
    today = date.today().strftime("%d-%b-%Y")
    
    plantinfo["details_query_date"] = today 
    plantinfo["ultimate_height"] = find_size(soup=soup, string="Ultimate height")
    plantinfo["time_to_ultimate_height"] = find_size(soup=soup, string="Time to ultimate height")
    plantinfo["ultimate_spread"] = find_size(soup=soup, string="Ultimate spread")

    position_dict = {'Full sun':0, 'Full shade':0, 'Partial shade':0}
    for k in position_dict:
        result = soup.find(string=k)
        if result is None:
            position_dict[k] = 0
        else:
            position_dict[k] = 1
    plantinfo["sunlight_full_sun"] = position_dict['Full sun']
    plantinfo["sunlight_full_shade"] = position_dict['Full shade']
    plantinfo["sunlight_partial_shade"] = position_dict['Partial shade']

    h = soup.find("span", string = re.compile("^H[0-9]$"))
    if h is not None:
        plantinfo["rhs_hardiness_rating"] = h.string
    else:
        plantinfo["rhs_hardiness_rating"] = ''

    f = soup.find("dt", string="Foliage")
    if f is not None:
        plantinfo["foliage"] = f.parent.contents[1].contents[0].text
    else:
        plantinfo["foliage"] = ''

    l = soup.find_all("span", {"class": "ng-star-inserted"})

    plantinfo["moisture_moist_but_well_drained"] = 0
    plantinfo["moisture_well_drained"] = 0
    plantinfo["moisture_poorly_drained"] = 0

    for i in l:
        s = i.string
        if s is not None:
            if re.sub("[^a-zA-Z]+", "", s) == "Moistbutwelldrained":
                plantinfo["moisture_moist_but_well_drained"] = 1
            if re.sub("[^a-zA-Z]+", "", s) == "Welldrained":
                plantinfo["moisture_well_drained"] = 1
            if re.sub("[^a-zA-Z]+", "", s) == "Poorlydrained":
                plantinfo["moisture_poorly_drained"] = 1

    plantinfo["acidity_acid"] = 0
    plantinfo["acidity_neutral"] = 0
    plantinfo["acidity_alkaline"] = 0

    for i in l:
        s = i.string
        if s is not None:
            if re.sub("[^a-zA-Z]+", "", s) == "Acid":
                plantinfo["acidity_acid"] = 1
            if re.sub("[^a-zA-Z]+", "", s) == "Neutral":
                plantinfo["acidity_neutral"] = 1
            if re.sub("[^a-zA-Z]+", "", s) == "Alkaline":
                plantinfo["acidity_alkaline"] = 1

    return plantinfo


if __name__ == '__main__':
    main()