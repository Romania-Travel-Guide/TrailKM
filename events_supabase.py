#####################################################################
# Call:
# python events_supabase <ini_file.ini>
#   ini_file.ini - is optional, by default it is config.ini
# Based on trailKM_supabase, the script stores POI data in supabase
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
import os
from random import randint
import time
import xmltodict
import supabase
import logging as log
import sys


# global variables
number_of_events = 0
# Get today's date
today = date.today()

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
def get_region_data():
    global number_of_events

    url = (
        "https://www.outdooractive.com/api/project/"
        + OA_PROJECT
        + "/events"
        + "?key="
        + OA_KEY
    )
    print(url)

    if OA_AREA != 0:
        url = url + "&area=" + OA_AREA

    log.debug("Get region URL:" + url)
    try:
        region_xml = xmltodict.parse(session.get(url).text)

    except Exception as e:
        print("ERROR:", e)
        log.error(e)
        return

    events = region_xml["datalist"]["data"]
    number_of_events = len(events)

    for event in events:
        # Query supabase to check if trail is already saved
        response = (
            supabase_client.table("events")
            .select("*")
            .eq("event_id", event["@id"])
            .execute()
        )
        if len(response.data) > 0:
            # Trail already in database
            # duration_minutes = response.data[0]["duration"]
            # length_meters = response.data[0]["distance"]
            # total_duration_minutes = total_duration_minutes + int(duration_minutes)
            # total_length_meters = total_length_meters + float(length_meters)
            # if str(response.data[0]["region_name"]) == "None":
            #     update_trail_data(data)
            print(".", end="")
        else:
            data = read_event_data(event["@id"])
            insert_event_data(data)


def insert_event_data(data):
    print("Inserting POI " + data["event_id"])
    data["new"] = True
    try:
        response = supabase_client.table("events").insert(data).execute()
        check_operation_result(response, "events", "insert")
    except Exception as e:
        print("ERROR:", e)
        log.error(e)
        return


#
# Read the POI parameters via Outdooractive API
#
def read_event_data(event_id):
    global OA_PROJECT
    # New trail, has to be recoreded in database
    wait()
    url = (
        "https://www.outdooractive.com/api/project/"
        + OA_PROJECT
        + "/oois/"
        + str(event_id)
        + "?key="
        + OA_KEY
        + "&lang=ro"
    )
    log.debug("Condition URL:" + url)
    print(url)

    try:
        event_xml = xmltodict.parse(session.get(url).text)
    except Exception as e:
        print("ERROR:", e)
        log.error(e)
        return
    event_title = ""
    try:
        event_title = event_xml["oois"]["event"]["title"]
    except KeyError:
        pass

    lang = ""
    try:
        if isinstance(event_xml["oois"]["event"]["localizedTitle"], list):
            lang = event_xml["oois"]["event"]["localizedTitle"][0]["@lang"]
        else:
            lang = event_xml["oois"]["event"]["localizedTitle"]["@lang"]
    except KeyError:
        pass

    region_name = ""
    district_name = ""
    customarea = ""
    try:
        if isinstance(event_xml["oois"]["event"]["regions"]["region"], list):
            for region in event_xml["oois"]["event"]["regions"]["region"]:
                if region["@type"] == "tourismarea":
                    region_name = region_name + " " + region["@name"]
                if region["@type"] == "customarea":
                    customarea = customarea + " " + region["@id"]
                if region["@type"] == "district":
                    district_name = district_name + " " + region["@id"]
    except KeyError:
        pass

    ranking = 0
    try:
        ranking = event_xml["oois"]["event"]["@ranking"]
    except KeyError:
        pass
    destination = 0
    try:
        destination = event_xml["oois"]["event"]["@destination"]
    except KeyError:
        pass
    frontendtype = ""
    try:
        frontendtype = event_xml["oois"]["event"]["@frontendtype"]
    except KeyError:
        pass
    category = 0
    try:
        category = event_xml["oois"]["event"]["category"]["@id"]
    except KeyError:
        pass
    category_name = ""
    try:
        category_name = event_xml["oois"]["event"]["category"]["@name"]
    except KeyError:
        pass
    datatype = ""
    try:
        datatype = event_xml["oois"]["event"]["category"]["datatype"]
    except KeyError:
        pass

    author = ""
    try:
        author = event_xml["oois"]["event"]["meta"]["authorFull"]["name"]
    except KeyError:
        author = ""
    author_id = 0
    try:
        author_id = event_xml["oois"]["event"]["meta"]["authorFull"]["id"]
    except KeyError:
        author_id = 0

    date_created = ""
    try:
        date_created = event_xml["oois"]["event"]["meta"]["date"]["@created"]
    except KeyError:
        pass
    date_lastModified = ""
    try:
        date_lastModified = event_xml["oois"]["event"]["meta"]["date"]["@lastModified"]
    except KeyError:
        pass
    date_firstPublish = ""
    try:
        date_firstPublish = event_xml["oois"]["event"]["meta"]["date"]["@firstPublish"]
    except KeyError:
        pass
    primaryImage = ""
    try:
        primaryImage = event_xml["oois"]["event"]["primaryImage"]["@id"]
    except KeyError:
        pass
    data = {
        "title": event_title,
        "lang": lang,
        "destination": destination,
        "frontendtype": frontendtype,
        "ranking": ranking,
        "event_id": event_id,
        "author": author,
        "author_id": author_id,
        "category": category,
        "category_name": category_name,
        "datatype": datatype,
        "region": str(OA_AREA),
        "date_created": date_created,
        "date_lastModified": date_lastModified,
        "date_firstPublish": date_firstPublish,
        "region_name": region_name.strip(),
        "district_name": district_name.strip(),
        "customarea": customarea.strip(),
        "primaryImage": primaryImage,
        "lang": lang,
        "project": OA_PROJECT,
    }
    return data


def set_new_to_false():
    data = {
        "new": False,
    }
    response = (
        supabase_client.table("events")
        .update(data)
        .eq("new", "True")
        .eq("project", OA_PROJECT)
        .execute()
    )


def main():
    global SUPABASE_URL, SUPABASE_KEY, OA_AREA, OA_PROJECT, today

    log.basicConfig(
        filename=config["Log"]["File"],
        level=os.environ.get("LOGLEVEL", config["Log"]["Level"]),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S ",
    )

    log.info("===============================")
    log.info(
        "Program start: " + str(datetime.datetime.today().strftime("%Y-%m-%d %H:%M"))
    )
    log.info("===============================")
    # Do not reset new trails
    # set_new_to_false()
    get_region_data()
    # Prepare the data to be inserted
    data = {
        "date": today.isoformat(),
        "total_events": number_of_events,
        "region": str(OA_AREA),
        "project": OA_PROJECT,
    }
    response = (
        supabase_client.table("DailyStats")
        .select("*")
        .eq("date", today)
        .eq("region", OA_AREA)
        .eq("project", OA_PROJECT)
        .execute()
    )
    if len(response.data) > 0:
        print("Updating data")
        try:
            response = (
                supabase_client.table("DailyStats")
                .update(data)
                .eq("date", today)
                .eq("region", OA_AREA)
                .eq("project", OA_PROJECT)
                .execute()
            )
        except:
            return
        check_operation_result(response, "Daily trail statistics", "update")
    else:
        print("Insering data")
        try:
            response = supabase_client.table("DailyStats").insert(data).execute()
        except Exception as e:
            print("ERROR:", e)
            log.error(e)
            return
        check_operation_result(response, "Daily trail statistics", "insert")


def check_operation_result(response, entity_name, operation):
    if len(response.data) > 0:
        print(f"{entity_name} {operation}ed successfully.")
    else:
        print(f"Failed to {operation} {entity_name}.")
        print(f"Error: {response.error}")


if __name__ == "__main__":
    main()
