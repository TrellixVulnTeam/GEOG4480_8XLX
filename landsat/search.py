#!/usr/bin/env python3
"""
Script tp search for an order Landsat scenes using the USGS JSON API

Information on the API can be found at:
https://earthexplorer.usgs.gov/inventory/documentation/json-api

Isaac Wismer
wismeri@uoguelph.ca
GEOG*4480 W19
March 6 2019

Created for a project on wildfire vulnerability in Mackenzie County in Alberta
"""

import json
import pprint

import requests

# prints out the dictionaries nicely
pp = pprint.PrettyPrinter(indent=2)

search_url = "https://earthexplorer.usgs.gov/inventory/json/v/1.4.0/"

username = "username"
password = "password"

# Generate API key to be able to search
params = {"username": username,
          "password": password
          }
r = requests.post(search_url + "login",
                  params={'jsonRequest': json.dumps(params)})

api_key = r.json()['data']


def search_api(endpoint: str, data: dict) -> dict:
    r = requests.get(
        search_url + endpoint, params={'jsonRequest': json.dumps(data)})
    return r.json()


# See what datasets there are for landsat 7
# r = requests.get(
#     url + "datasets", params={'jsonRequest': f'{{"apiKey": "{api_key}", "datasetName": "LANDSAT_ETM_C1"}}'})
# pp.pprint(r.json())


# Get a list of the fields for the dataset
# params = {"apiKey": f"{api_key}",
#           "datasetName": "LANDSAT_ETM_C1"
#           }
# r = requests.get(
#     url + "datasetfields", params={'jsonRequest': json.dumps(params)})
# pp.pprint(r.json())

# Search for scenes
scenes = {}
# Do one year at a time, 2013-2017
for year in range(2013, 2018):

    # Make search params
    params = {"apiKey": f"{api_key}",
              # Landsat 7 level 1
              "datasetName": "LANDSAT_ETM_C1",
              # Only may - october
              "temporalFilter": {
                  "startDate": f"{year}-05-01",
                  "endDate": f"{year}-10-31"
              },
              "months": [5, 6, 7, 8, 9, 10],
              #   Specify what bands I want
              "additionalCriteria": {
                  "filterType": "and",
                  "childFilters": [
                      {
                          "filterType": "or",
                          "childFilters": [
                              #   Path 45-47, row 18-20
                              {
                                "filterType": "and",
                                "childFilters": [
                                    {"filterType": "between",
                                     "fieldId": 19884,
                                     "firstValue": "45",
                                     "secondValue": "47"},
                                    {"filterType": "between",
                                     "fieldId": 19887,
                                     "firstValue": "18",
                                     "secondValue": "20"},
                                ]
                              },
                              #   Path 48-49 row 18-19
                              {
                                  "filterType": "and",
                                  "childFilters": [
                                      {"filterType": "between",
                                       "fieldId": 19884,
                                       "firstValue": "48",
                                       "secondValue": "49"},
                                      {"filterType": "between",
                                          "fieldId": 19887,
                                          "firstValue": "18",
                                          "secondValue": "19"},
                                  ]
                              },
                              #   path 44 row 19-20
                              {
                                  "filterType": "and",
                                  "childFilters": [
                                      {"filterType": "value",
                                       "fieldId": 19884,
                                       "value": "48",
                                       "operand": "="},
                                      {"filterType": "between",
                                          "fieldId": 19887,
                                          "firstValue": "19",
                                          "secondValue": "20"},
                                  ]
                              },
                              #   Path 43, row 20
                              {
                                  "filterType": "and",
                                  "childFilters": [
                                      {"filterType": "value",
                                       "fieldId": 19884,
                                       "value": "43",
                                       "operand": "="},
                                      {"filterType": "value",
                                          "fieldId": 19887,
                                          "value": "20",
                                          "operand": "="},
                                  ]
                              },
                          ]
                      },
                      #   Only day scenes
                      {"filterType": "value",
                          "fieldId": 19885,
                          "value": "DAY",
                          "operand": "="}
                  ]
              },
              "maxCloudCover": 60,
              # There are about 100 scenes per year, so 1000 is plenty
              "maxResults": 1000
              }
    r = search_api("search", params)
    # pp.pprint(r)
    to_order = [result['displayId'] for result in r['data']['results']]
    good_scenes = []
    # Remove specific scenes where surface reflectance data is not available
    # If I don't remove these, it will cause an error when I try to order them
    for result in to_order:
        # pp.pprint(result)
        # print(result)
        if result not in ('LE07_L1TP_046018_20160601_20161010_01_T1',
                          'LE07_L1TP_047018_20160608_20161010_01_T1',
                          'LE07_L1TP_045018_20160610_20161210_01_T1',
                          'LE07_L1TP_045019_20160610_20161210_01_T1',
                          'LE07_L1TP_045020_20160610_20161209_01_T1',
                          ):
            good_scenes.append(result)
    to_order = good_scenes

    scenes[year] = to_order.copy()


# Destroy the API key
r = search_api("logout", {'api_key': api_key})

# Now that I have the scenes to order, use the order API
order_url = "https://espa.cr.usgs.gov/"

pp.pprint(scenes)

# r = requests.get(order_url + "api/v1", auth=(username, password))

# pp.pprint(r.json())

# Order each year
for year, to_order in scenes.items():

    params = {
        'inputs': to_order
    }
    r = requests.get(order_url + "api/v1/available-products",
                     auth=(username, password), json=params)
    pp.pprint(r.json())

    # Specify what to order
    params = {
        "etm7_collection": {
            "inputs": to_order,
            "products": ['sr_ndmi']
        },
        "format": "gtiff",
        "note": f"year {year}"
    }
    r = requests.post(order_url + "api/v1/order",
                      auth=(username, password), json=params)
    pp.pprint(r.json())
