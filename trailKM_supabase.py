#####################################################################
# Call:
# python trailKM_supabase <ini_file.ini>
#   ini_file.ini - is optional, by default it is config.ini
# Based on trailKM, the script stores trail statistic data in supabase
#
# Prerequisite:
#  API access for Outdooractive, see
#  http://developers.outdooractive.com/API-Reference/Data-API.html
#
#####################################################################
# Version: 0.9.0
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
import sys

# global variables
number_of_trails = 0
total_duration_minutes = 0
total_length_meters = 0
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
OA_LANG = config["Interface"]["OUTDOORACTIVE_LANGUAGE"]
try:
    OA_AREA = config["Interface"]["OUTDOORACTIVE_REGION"]
except:
    OA_AREA = 0
SUPABASE_URL = config["Interface"]["SUPABASE_URL"]
SUPABASE_KEY = config["Interface"]["SUPABASE_KEY"]
try:
    SUPABASE_PREFIX = config["Interface"]["SUPABASE_TABLE_PREFIX"]
except:
    SUPABASE_PREFIX = ""

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
    global total_duration_minutes
    global total_length_meters
    global OA_PROJECT

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
    try:
        region_xml = xmltodict.parse(session.get(url).text)

    except Exception as e:
        print("ERROR:", e)
        log.error(e)
        return

    trails = region_xml["datalist"]["data"]
    number_of_trails = len(trails)

    for trail in trails:
        # Query supabase to check if trail is already saved
        response = (
            supabase_client.table(SUPABASE_PREFIX + "Trails")
            .select("*")
            .eq("trail_id", trail["@id"])
            .eq("project", OA_PROJECT)
            .execute()
        )
        if len(response.data) > 0:
            # Trail already in database
            duration_minutes = response.data[0]["duration"]
            length_meters = response.data[0]["distance"]
            total_duration_minutes = total_duration_minutes + int(duration_minutes)
            total_length_meters = total_length_meters + float(length_meters)
            if str(response.data[0]["region_name"]) == "None":
                update_trail_data(data)
        else:
            data = read_trail_data(trail["@id"])
            insert_trail_data(data)


def insert_trail_data(data):
    print("Inserting trail " + data["trail_id"])
    data["new"] = True
    try:
        response = (
            supabase_client.table(SUPABASE_PREFIX + "Trails").insert(data).execute()
        )
        check_operation_result(response, "Trails", "insert")
    except Exception as e:
        print("ERROR:", e)
        log.error(e)
        return


def update_trail_data(data):
    global OA_PROJECT

    print("Updating trail " + data["trail_id"])
    data["new"] = False
    try:
        response = (
            supabase_client.table(SUPABASE_PREFIX + "Trails")
            .update(data)
            .eq("trail_id", data["trail_id"])
            .eq("project", OA_PROJECT)
            .execute()
        )
        check_operation_result(response, "Trails", "update")
    except Exception as e:
        print("ERROR:", e)
        log.error(e)
        return


#
# Read the trails parameters via Outdooractive API
#
def read_trail_data(trail_id):
    global total_duration_minutes
    global total_length_meters
    global OA_PROJECT

    # New trail, has to be recoreded in database
    wait()
    url = (
        "https://www.outdooractive.com/api/project/"
        + OA_PROJECT
        + "/oois/"
        + str(trail_id)
        + "?key="
        + OA_KEY
        + "&lang="
        + OA_LANG
    )
    log.debug("Condition URL:" + url)
    print(url)

    try:
        trail_xml = xmltodict.parse(session.get(url).text)
    except Exception as e:
        print("ERROR:", e)
        log.error(e)
        return
    trail_name = ""
    try:
        trail_name = trail_xml["oois"]["tour"]["title"]
    except KeyError:
        pass

    lang = OA_LANG
    try:
        if isinstance(trail_xml["oois"]["tour"]["localizedTitle"], list):
            lang = trail_xml["oois"]["tour"]["localizedTitle"][0]["@lang"]
        else:
            lang = trail_xml["oois"]["tour"]["localizedTitle"]["@lang"]
    except KeyError:
        pass

    region_name = ""
    district_name = ""
    customarea = ""

    if trail_xml["oois"]["tour"]["regions"] is not None:
        try:
            if isinstance(trail_xml["oois"]["tour"]["regions"]["region"], list):
                for region in trail_xml["oois"]["tour"]["regions"]["region"]:
                    if region["@type"] == "tourismarea":
                        region_name = region_name + " " + region["@name"]
                    if region["@type"] == "customarea":
                        customarea = customarea + " " + region["@id"]
                    if region["@type"] == "district":
                        district_name = district_name + " " + region["@id"]
        except KeyError:
            pass

    duration_minutes = 0
    try:
        duration_minutes = trail_xml["oois"]["tour"]["time"]["@min"]
    except KeyError:
        pass
    length_meters = 0
    try:
        length_meters = trail_xml["oois"]["tour"]["length"]
    except KeyError:
        pass
    ranking = 0
    try:
        ranking = trail_xml["oois"]["tour"]["@ranking"]
    except KeyError:
        pass
    author = ""
    try:
        author = trail_xml["oois"]["tour"]["meta"]["authorFull"]["name"]
    except KeyError:
        author = ""
    author_id = 0
    try:
        author_id = trail_xml["oois"]["tour"]["meta"]["authorFull"]["id"]
    except KeyError:
        author_id = 0
    difficulty = 0
    try:
        difficulty = trail_xml["oois"]["tour"]["rating"]["@difficulty"]
    except KeyError:
        pass
    category = 0
    try:
        category = trail_xml["oois"]["tour"]["category"]["@id"]
    except KeyError:
        pass
    date_created = ""
    try:
        date_created = trail_xml["oois"]["tour"]["meta"]["date"]["@created"]
    except KeyError:
        pass
    date_lastModified = ""
    try:
        date_lastModified = trail_xml["oois"]["tour"]["meta"]["date"]["@lastModified"]
    except KeyError:
        pass
    date_firstPublish = ""
    try:
        date_firstPublish = trail_xml["oois"]["tour"]["meta"]["date"]["@firstPublish"]
    except KeyError:
        pass
    primaryImage = ""
    try:
        primaryImage = trail_xml["oois"]["tour"]["primaryImage"]["@id"]
    except KeyError:
        pass
    data = {
        "name": trail_name,
        "lang": lang,
        "distance": length_meters,
        "duration": duration_minutes,
        "ranking": ranking,
        "trail_id": trail_id,
        "author": author,
        "author_id": author_id,
        "difficulty": difficulty,
        "category": category,
        "region": str(OA_AREA),
        "date_created": date_created,
        "date_lastModified": date_lastModified,
        "date_firstPublish": date_firstPublish,
        "region_name": region_name.strip(),
        "district_name": district_name.strip(),
        "customarea": customarea.strip(),
        "primaryImage": primaryImage,
        "project": OA_PROJECT,
    }
    return data


def set_new_to_false():
    global OA_PROJECT
    data = {
        "new": False,
    }
    response = (
        supabase_client.table(SUPABASE_PREFIX + "Trails")
        .update(data)
        .eq("new", "True")
        .eq("project", OA_PROJECT)
        .execute()
    )


def main():
    global SUPABASE_URL, SUPABASE_KEY, OA_AREA, OA_PROJECT, today

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
        "total_trails": number_of_trails,
        "total_distance": int(total_length_meters / 1000),
        "total_duration": str(timedelta(minutes=total_duration_minutes)),
        "region": str(OA_AREA),
        "project": OA_PROJECT,
    }
    response = (
        supabase_client.table(SUPABASE_PREFIX + "DailyStats")
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
                supabase_client.table(SUPABASE_PREFIX + "DailyStats")
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
            response = (
                supabase_client.table(SUPABASE_PREFIX + "DailyStats")
                .insert(data)
                .execute()
            )
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
