# Unit tests for RHS scraping scripts

import subprocess
import pytest
import os
import json

cwd = os.getcwd()
wd=os.path.dirname(cwd)
outfile = 'unit_test_out.txt'
enrichedfile = 'unit_test_out_enriched.txt'


# Test find_plants.py
@pytest.mark.order(1)
def test_find_plants():


    if os.path.exists(outfile):
        os.remove(outfile)
        print("Previous version of " + outfile + " deleted.")

    cmd = 'python find_plants.py -o ' + cwd + '\\' + outfile + ' "Crataegus&isAgm=true"'
    print("Running this CLI command: " + cmd) 
    subprocess.run(cmd, cwd=wd)

    with open (outfile, "r") as f:
        result = f.read()

    assert "C. orientalis is a small, spreading, thorny, deciduous tree to around 6m tall" in result
    
    
# Test add_plant_details.py
@pytest.mark.order(2)
def test_add_plant_details():

    if os.path.exists(enrichedfile):
        os.remove(enrichedfile)
        print("Previous version of " + enrichedfile + " deleted.")

    cmd = 'python add_plant_details.py -o ' + cwd + '\\' + enrichedfile + ' ' + cwd + '\\' + outfile
    print("Running this CLI command: " + cmd) 
    subprocess.run(cmd, cwd=wd)   

    with open (enrichedfile, "r") as f:
        result = json.load(f)

    #assert len(result['data']) == 7
    assert len(result['data'][0]) == 29