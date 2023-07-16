#####################################################################
# Call:
# python conditions_supabase <ini_file.ini>
#   ini_file.ini - is optional, by default it is config.ini
# Based on trailKM_supabase, the script stores POI data in supabase
#
# Prerequisite:
#  API access for Outdooractive, see
#  http://developers.outdooractive.com/API-Reference/Data-API.html
#
#####################################################################
# Version: 0.2.1
# Email: paul.wasicsek@gmail.com
# Status: dev
#####################################################################

import configparser
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import datetime
from datetime import timedelta, date
import os
from random import randint
import time
import xmltodict
import supabase
import logging as log
import sys


# global variables
today = date.today()
condition_xml = {}

try:
    config_file = sys.argv[1]
except:
    config_file = "config.ini"

print("Config file: " + config_file)
# Read initialization parameters
config = configparser.ConfigParser()
try:
    config.read(config_file)
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
def get_region_conditions():
    global region_xml

    url = (
        "https://www.outdooractive.com/api/project/"
        + OA_PROJECT
        + "/conditions?key="
        + OA_KEY
    )
    log.debug("Base URL:" + url)
    print(url)

    if OA_AREA != 0:
        url = url + "&area=" + OA_AREA
    log.debug("Get region URL:" + url)

    # Read all the conditions you have access to through API
    try:
        region_xml = xmltodict.parse(session.get(url).text)
    except Exception as e:
        print("ERROR:", e)
        log.error(e)
        return

    for condition in region_xm ta)


def insert_condition(data):
    print("Inserting condition " + data["condition_id"])
    try:
        response = supabase_client.table("Conditions").insert(data).execute()
        check_operation_result(response, "Conditions", "insert")
    except Exception as e:
        print("ERROR:", e)
        log.error(e)
        return


def update_condition(data):
    print("Updating condition " + data["condition_id"])
    try:
        response = (
            supabase_client.table("Conditions")
            .update(data)
            .eq("condition_id", data["condition_id"])
            .eq("project", data["project"])
            .execute()
        )
        check_operation_result(response, "Conditions", "update")
    except Exception as e:
        print("ERROR:", e)
        log.error(e)
        return


#
# Read the POI parameters via Outdooractive API
#
def read_condition(condition_id):
    global OA_PROJECT, condition_xml

    # New trail, has to be recoreded in database
    wait()
    url = (
        "https://www.outdooractive.com/api/project/"
        + OA_PROJECT
        + "/oois/"
        + str(condition_id)
        + "?key="
        + OA_KEY
        + "&lang=ro"
    )
    log.debug("Condition URL:" + url)
    print(url)

    try:
        condition_xml = xmltodict.parse(session.get(url).text)
    except Exception as e:
        print("ERROR:", e)
        log.error(e)
        return

    # print(condition_xml)
    # exit()
    condition_id = ""
    try:
        condition_id = condition_xml["oois"]["condition"]["@id"]
    except KeyError:
        pass
    condition_title = ""
    try:
        condition_title = condition_xml["oois"]["condition"]["title"]
    except KeyError:
        pass

    lang = ""
    try:
        if isinstance(condition_xml["oois"]["condition"]["localizedTitle"], list):
            lang = condition_xml["oois"]["condition"]["localizedTitle"][0]["@lang"]
        else:
            lang = condition_xml["oois"]["condition"]["localizedTitle"]["@lang"]
    except KeyError:
        pass

    state = ""
    try:
        state = condition_xml["oois"]["condition"]["meta"]["workflow"]["@state"]
    except KeyError:
        pass
    print(state)

    category = ""
    try:
        category = condition_xml["oois"]["condition"]["category"]["@id"]
    except KeyError:
        pass

    category_name = ""
    try:
        category_name = condition_xml["oois"]["condition"]["category"]["@name"]
    except KeyError:
        pass

    ranking = 0
    try:
        ranking = condition_xml["oois"]["condition"]["@ranking"]
    except KeyError:
        pass

    dayOfInspection = ""
    try:
        dayOfInspection = condition_xml["oois"]["condition"]["@dayOfInspection"]
    except KeyError:
        pass

    dateFrom = None
    try:
        dateFrom = condition_xml["oois"]["condition"]["@dateFrom"]
    except KeyError:
        pass

    validTo = None
    try:
        validTo = condition_xml["oois"]["condition"]["@validTo"]
    except KeyError:
        pass

    frontendtype = 0
    try:
        frontendtype = condition_xml["oois"]["condition"]["@frontendtype"]
    except KeyError:
        pass

    datatype = ""
    try:
        datatype = condition_xml["oois"]["condition"]["category"]["datatype"]
    except KeyError:
        pass

    author_id = 0
    try:
        author_id = condition_xml["oois"]["condition"]["meta"]["authorFull"]["id"]
    except KeyError:
        pass
    author = ""
    try:
        author = condition_xml["oois"]["condition"]["meta"]["authorFull"]["name"]
    except KeyError:
        try:
            author = condition_xml["oois"]["condition"]["meta"]["author"]
        except KeyError:
            pass
    longText = ""
    try:
        longText = condition_xml["oois"]["condition"]["longText"]
    except KeyError:
        pass
    winterActivity = ""
    try:
        winterActivity = condition_xml["oois"]["condition"]["winterActivity"]
    except KeyError:
        pass
    geometry = ""
    try:
        geometry = condition_xml["oois"]["condition"]["geometry"]
    except KeyError:
        pass
    riskDescription = ""
    try:
        riskDescription = condition_xml["oois"]["condition"]["riskDescription"]
    except KeyError:
        pass
    weatherDescription = ""
    try:
        weatherDescription = condition_xml["oois"]["condition"]["weatherDescription"]
    except KeyError:
        pass
    primaryImage = ""
    try:
        primaryImage = condition_xml["oois"]["condition"]["primaryImage"]["@id"]
    except KeyError:
        pass
    workflow_status = ""
    try:
        workflow_status = condition_xml["oois"]["condition"]["meta"]["workflow"][
            "@state"
        ]
    except KeyError:
        pass
    # geometry_description = ""
    # for record in condition_xml["oois"]["condition"]["regions"]["region"]:
    #     # print(str(record["@id"]))
    #     geometry_description = geometry_description + get_region(record)

    data = {
        "condition_id": condition_id,
        "title": condition_title,
        "lang": lang,
        "status": state,
        "category_id": category,
        "ranking": ranking,
        "day_of_inspection": dayOfInspection,
        "date_from": dateFrom,
        "valid_to": validTo,
        "frontendtype": frontendtype,
        "datatype": datatype,
        "author_id": author_id,
        "author": author,
        "long_text": longText,
        "winter_activity": winterActivity,
        "geometry": geometry,
        "risk_description": riskDescription,
        "weather_description": weatherDescription,
        # "geometry_description": geometry_description,
        "category_name": category_name,
        "primaryImage": primaryImage,
        "project": OA_PROJECT,
    }
    return data


def check_operation_result(response, entity_name, operation):
    if len(response.data) > 0:
        print(f"{entity_name} {operation}ed successfully.")
    else:
        print(f"Failed to {operation} {entity_name}.")
        print(f"Error: {response.error}")


# Check if conditions stored in supabase are still active
# by searching the stored condition_id with the one returned by the API call
# If it is not included in the API call, update status as "rejected"
def status_stored_conditions():
    global OA_PROJECT
    global region_xml

    response = (
        supabase_client.table("Conditions")
        .select("condition_id")
        .eq("project", OA_PROJECT)
        .execute()
    )
    # print(response.data)
    # print("region_xml")
    # print(region_xml)
    if len(response.data) > 0:
        # Condition already in database
        for stored_condition in response.data:
            print(stored_condition["condition_id"])
            for condition in region_xml["datalist"]["data"]:
                if stored_condition == condition["@id"]:
                    return True
    return False


def main():
    global SUPABASE_URL, SUPABASE_KEY, OA_AREA, OA_PROJECT, today

    log.info("===============================")
    log.info(
        "Program start: " + str(datetime.datetime.today().strftime("%Y-%m-%d %H:%M"))
    )
    log.info("===============================")

    get_region_conditions()
    status_stored_conditions()
    print(
        str(datetime.datetime.today().strftime("%Y-%m-%d %H:%M"))
        + " [END] conditions.py"
    )


if __name__ == "__main__":
    main()
