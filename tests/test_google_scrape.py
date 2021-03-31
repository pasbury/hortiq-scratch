# Unit tests for google price scraping script

import subprocess
import pytest
import os
import json

cwd = os.getcwd()
wd=os.path.dirname(cwd)
infile = 'plants_unit_test.txt'
mapfile = 'google_map_unit_test_out.txt'
buyingfile = 'google_buying_unit_test_out.txt'

# test running the script on small sample file

def test_run_script():
    
    if os.path.exists(mapfile):
        os.remove(mapfile)
        print("Previous version of " + mapfile + " deleted.")
        
    if os.path.exists(buyingfile):
        os.remove(buyingfile)
        print("Previous version of " + buyingfile + " deleted.")

    cmd = 'python get_google_shopping_info.py -mf ' + cwd + '\\' + mapfile + ' -bf ' + cwd + '\\' + buyingfile + ' ' + cwd + '\\' + infile
    print("Running this CLI command: " + cmd) 
    cp = subprocess.run(cmd, cwd=wd, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    assert cp.returncode == 0, cp.output


# Test find_plants.py

def test_map_file():

    with open (mapfile, "r") as f:
        result = json.load(f)

    assert len(result['data']) > 0, "No data in " + mapfile
    
    
# Test add_plant_details.py

def test_buying_file():

    with open (buyingfile, "r") as f:
        result = json.load(f)
    
    assert len(result['data']) > 0, "No data in " + buyingfile