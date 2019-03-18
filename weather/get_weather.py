#!/usr/bin/env python3
"""
GEOG*4480 W19
Isaac Wismer
wismeri@uoguelph.ca

Script to retreive weather data from the Current and Historical Alberta Weather
Station Data Viewer
The service was not designed to be a REST API, I reverse engineered it so that
I wouldn't have to use the web interface

This script creates rasters for monthly weather data from 14 weather stations
It interpolates the data between the stations
"""

import csv
import sys
import time

import requests
from bs4 import BeautifulSoup

weather_station_data = {}

with open('stations.csv', 'r') as f:
    reader = csv.DictReader(f)
    stations = [row for row in reader]
    # for row in reader:
    #     print(row['name'])

start_date = '20180501'
end_date = '20181031'
station = '64350'
# Taken from the cookie 
session = '0000A818mL0oXMD4atua0-maZUN:17r8ultq0'

# Do one query for each year
for year in range(2005, 2018):
    start_date = f"{year}0501"
    end_date = f"{year}1031"
    for i in range(0, len(stations), 5):
        status = 400
        # Get the first 5 stations
        station = ",".join([s['id'] for s in stations[i:i + 5]])
        print(f"Getting staions: {', '.join([s['name'] for s in stations[i:i + 5]])}")
        # Loop until it works
        while status > 200:
            # make the URL
            url = f'https://agriculture.alberta.ca/acis/api/v1/legacy/weather-data/timeseries?stations={station}&elements=PRCIP,ATAM,HUAM,WSAM&startdate={start_date}&enddate={end_date}&interval=DAILY&format=HTML&precipunit=mm&inclCompleteness=false&inclSource=false&inclComments=false'
            # Set the Headers
            headers = {
                'session': session[4:27],
                'Cookie': f'JSESSIONID={session}; geographicRegion=Alberta',
                'Accept': 'text/html, */*; q=0.01',
                'Host': 'agriculture.alberta.ca',
                'User-Agent': f'{session}',
                'Referer': 'https://agriculture.alberta.ca/acis/alberta-weather-data-viewer.jsp',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.5'
            }
            # Make the request
            r = requests.get(url, headers=headers)
            # print(r.status_code)
            status = r.status_code
            # If there was an error, it was probably because the session key
            # was used too many times. So get a new one and try again
            if status > 200:
                print(f"Error retreiving data. Code: {status} {r.text}")
                print(f"Session ID: {session}")
                if status in (429, 403):
                    session = input("Please enter a new session ID: ")
                else:
                    print(f"Unknown Error: {status} {r.text}")
                    sys.exit(1)

        # Parse the response
        soup = BeautifulSoup(r.text, 'html.parser')

        # Get the colum headers
        cols = [c.get_text() for c in soup.thead.find_all('th')]

        # Get the number of columns
        num_cols = len(cols)

        # Get all the column values
        tds = [t.get_text() for t in soup.find_all('td')]

        # group the values into rows
        rows = [tds[i:i + num_cols] for i in range(0, len(tds), num_cols)]

        # Group all the rows by station
        for row in rows:
            # Create a key for the weather station if it doesn't exist
            weather_station_data.setdefault(row[0], []).append(row)
            # Convert date to ISO
            row[1] = time.strftime("%Y-%m-%d", time.strptime(row[1], "%d-%B-%Y"))
            # print(time.strftime("%Y-%m-%d", time.strptime(row[1], "%d-%B-%Y")))

# Print to CSV
for key, rows in weather_station_data.items():
    with open(f'csv/{key}.csv', 'w') as w:
        writer = csv.writer(w)
        writer.writerow(cols[1:])
        for r in rows:
            writer.writerow(r[1:])
weather_station_data_monthly = {}

for key, rows in weather_station_data.items():
    # print(key)
    months = [[], [], [], [], [], []]
    for row in rows:
        date = time.strptime(row[1], "%Y-%m-%d")
        # print(date)
        months[date.tm_mon - 5].append(row)
    # print(months)
    month_avgs_precip = []
    for i, month in enumerate(months):
        # print(f"Month: {i + 5}")
        avg = sum([float(day[2]) if day[2] else 0.0 for day in month]) / len(month)
        # print(avg)
    weather_station_data_monthly[key] = months
