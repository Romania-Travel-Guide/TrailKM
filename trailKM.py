#####################################################################
# trailKM 
# 1. Determine how may km of trails do you have in your region
#
# Prerequisite:
#  API access for Outdooractive, see 
#  http://developers.outdooractive.com/API-Reference/Data-API.html
#
# OUTOPUT Example:
# Number of trails: 2978
# Number of kilometers: 239892.3
# Total duration: 1664 days, 9:40
#####################################################################
# Version: 0.0.1
# Email: paul.wasicsek@gmail.com
# Status: dev
#####################################################################

import configparser
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import datetime
from datetime import timedelta
import logging as log
import os
from random import randint
import time
import xmltodict

# global variables
number_of_trails = 0
total_duration_minutes = 0
total_length_meters = 0


# Read initialization parameters
config = configparser.ConfigParser()
try:
    config.read("config.ini")
except Exception as err:
    print("Cannot read INI file due to Error: %s" % (str(err)))

OA_PROJECT = config["Outdooractive"]["Project"]
OA_KEY = config["Outdooractive"]["API"]

log.basicConfig(
    filename=config["Log"]["File"],
    level=os.environ.get("LOGLEVEL", config["Log"]["Level"]),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S ",
)

# Improve https connection handling, see article:
# https://stackoverflow.com/questions/23013220/max-retries-exceeded-with-url-in-requests
#
session = requests.Session()
retry = Retry(connect=3, backoff_factor=0.5)
adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)
session.mount("https://", adapter)

#
# Wait according to seetings in config.ini (try not to send too many requests in a too short time)
#
def wait():
    if config["Action"]["Execute"] == "Delay":
        # Include a waiting period, so the algorithm doesn't think it's automatic processing
        t = randint(int(config["Wait"]["Min"]), int(config["Wait"]["Max"]))
        time.sleep(t)


#
# Return map region type and name based on region id
#
def get_region_data():
    global number_of_trails

    url = (
        "https://www.outdooractive.com/api/project/"
        + OA_PROJECT
        + "/filter/tour"
        + "?key="
        + OA_KEY
    )
    log.debug("Get region URL:" + url)
    region_xml = xmltodict.parse(session.get(url).text)
    trails=region_xml["datalist"]["data"]
    number_of_trails = len(trails)

    for trail in trails:
        read_trail_data(trail["@id"])


#
# Read the trails parameters via Outdooractive API 
#
def read_trail_data(trail):
    global trail_xml
    global total_duration_minutes
    global total_length_meters

    wait()
    url = (
        "https://www.outdooractive.com/api/project/"
        + OA_PROJECT
        + "/oois/"
        + str(trail)
        + "?key="
        + OA_KEY
        + "&lang=ro"
    )
    log.debug("Condition URL:" + url)
    trail_xml = xmltodict.parse(session.get(url).text)
    try:
        duration_minutes = trail_xml["oois"]["tour"]["time"]["@min"]
    except:
        duration_minutes = 0

    try:
        length_meters = trail_xml["oois"]["tour"]["length"]
    except:
        length_meters = 0

    total_duration_minutes = total_duration_minutes + int(duration_minutes)
    total_length_meters = total_length_meters + float(length_meters)

    

def main():
    get_region_data()
    print("Number of trails: %d" % number_of_trails)
    print("Number of kilometers: %.1f" % total_length_meters/1000)
    print("Total duration: %d" % str(timedelta(minutes=total_duration_minutes))[:-3])
    

if __name__ == "__main__":
    main()
