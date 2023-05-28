#####################################################################
# trailKM_supabase
# based on trail_KM, it stores trail statistic data in supabase
#
# Trails:
#    region varchar
#    name varchar
#    category varchar
#    distance numeric
#    duration time
#    difficulty varchar
#    ranking numeric
#    author varchar
#    trail_id numeric
#
# DailyStats:
#    date date
#    region varchar
#    total_trails bigint
#    total_distance numeric
#    total_duraction numeric
#    region varchar
#
# Prerequisite:
#  API access for Outdooractive, see
#  http://developers.outdooractive.com/API-Reference/Data-API.html
#
#####################################################################
# Version: 0.1.0
# Email: paul.wasicsek@gmail.com
# Status: dev
#####################################################################

import configparser
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import datetime
from datetime import timedelta, date
import logging as log
import os
from random import randint
import time
import xmltodict
import supabase

# global variables
number_of_trails = 0
total_duration_minutes = 0
total_length_meters = 0
# Get today's date
today = date.today()


# Read initialization parameters
config = configparser.ConfigParser()
try:
    config.read("config.ini")
except Exception as err:
    print("Cannot read INI file due to Error: %s" % (str(err)))

OA_PROJECT = config["Interface"]["OUTDOORACTIVE_PROJECT"]
OA_KEY = config["Interface"]["OUTDOORACTIVE_API"]
try:
    OA_AREA = config["Interface"]["OUTDOORACTIVE_REGION"]
except:
    OA_AREA = 0
SUPABASE_URL = config["Interface"]["SUPABASE_URL"]
SUPABASE_KEY = config["Interface"]["SUPABASE_KEY"]

log.basicConfig(
    filename=config["Log"]["File"],
    level=os.environ.get("LOGLEVEL", config["Log"]["Level"]),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S ",
)

# Improve https connection handling, see article:
# https://stackoverflow.com/questions/23013220/max-retries-exceeded-with-url-in-requests
session = requests.Session()
retry = Retry(connect=3, backoff_factor=0.5)
adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)
session.mount("https://", adapter)

# Initialize Supabase client
supabase_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)


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
    if OA_AREA != 0:
        url = url + "&area=" + OA_AREA

    log.debug("Get region URL:" + url)
    region_xml = xmltodict.parse(session.get(url).text)
    trails = region_xml["datalist"]["data"]
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

    try:
        trail_xml = xmltodict.parse(session.get(url).text)
    except:
        print("ERROR")

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

    if OA_AREA == 0:
        data = {
            "distance": length_meters,
            "duration": duration_minutes,
            "ranking": trail_xml["oois"]["tour"]["@ranking"],
            "trail_id": trail_xml["oois"]["tour"]["@id"],
            "author": trail_xml["oois"]["tour"]["meta"]["authorFull"]["name"],
            "difficulty": trail_xml["oois"]["tour"]["rating"]["@difficulty"],
            "category": trail_xml["oois"]["tour"]["category"]["@id"],
            "region": str(OA_AREA),
        }
        response = (
            supabase_client.table("Trails")
            .select("*")
            .eq("trail_id", trail_xml["oois"]["tour"]["@id"])
            .execute()
        )
        if len(response.data) > 0:
            print("Updating data - not implemented")
            # response = (
            #     supabase_client.table("Trails")
            #     .update(data)
            #     .eq("date", trail_xml["oois"]["tour"]["@id"])
            #     .execute()
            # )
            # check_operation_result(response, "Trails", "update")
        else:
            print("Insering data")
            response = supabase_client.table("Trails").insert(data).execute()
            check_operation_result(response, "Trails", "insert")


def main():
    global SUPABASE_URL, SUPABASE_KEY, OA_AREA, today

    get_region_data()
    # Prepare the data to be inserted
    data = {
        "date": today.isoformat(),
        "total_trails": number_of_trails,
        "total_distance": int(total_length_meters / 1000),
        "total_duration": str(timedelta(minutes=total_duration_minutes)),
        "region": str(OA_AREA),
    }
    response = (
        supabase_client.table("DailyStats").select("*").eq("date", "today").execute()
    )
    if len(response.data) > 0:
        print("Updating data")
        response = (
            supabase_client.table("DailyStats")
            .update(data)
            .eq("date", "today")
            .execute()
        )
        check_operation_result(response, "Daily trail statistics", "update")
    else:
        print("Insering data")
        response = supabase_client.table("DailyStats").insert(data).execute()
        check_operation_result(response, "Daily trail statistics", "insert")


def check_operation_result(response, entity_name, operation):
    if len(response.data) > 0:
        print(f"{entity_name} {operation}ed successfully.")
    else:
        print(f"Failed to {operation} {entity_name}.")
        print(f"Error: {response.error}")


if __name__ == "__main__":
    main()
