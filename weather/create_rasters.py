#!/usr/bin/env python3
"""
GEOG*4480 W19
Isaac Wismer
wismeri@uoguelph.ca

Created for a project on wildfire vulnerability in Mackenzie County in Alberta

This script creates rasters for monthly weather data from 14 weather stations
It interpolates the data between the stations

Run with:
./create_rasters.py dir/of/weather/csvs/ station/shapefile/ output/dir/
"""

import csv
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import fiona

csv_folder = Path(sys.argv[1])
station_shp = Path(sys.argv[2])
output_path = Path(sys.argv[3])
weather_types = ['temp', 'precip', 'humid', 'wind']

# Create subdirectories for each type of data
for wt in weather_types:
    Path.mkdir(output_path / wt, exist_ok=True)

# Create a temp directory in the current working directory
# it is deleted when the program finishes
tmp_path = Path("tmp")
Path.mkdir(tmp_path, exist_ok=True)

# Create an in memory SQLite DB
# This is much easier than creating some crazy data structure with dicts
db = sqlite3.connect(":memory:")
cur = db.cursor()

# This is a very simple table with no checking
# If this were used to store the data long term I would use a very different
# table structure
cur.execute('''
CREATE TABLE reading (
    reading_id INTEGER PRIMARY KEY,
    station TEXT,
    year INTEGER,
    month INTEGER,
    precip REAL,
    temp REAL,
    humid REAL,
    wind REAL
)
''')

# Read all the CSVs into the DB
for file in csv_folder.iterdir():
    # Skip non CSVs
    if not file.is_file() or file.suffix != ".csv":
        continue
    with file.open() as f:
        reader = csv.reader(f)
        # Read the header row and discard
        next(reader)
        for row in reader:
            # Parse the date
            date = time.strptime(row[0], "%Y-%m-%d")
            # print(f"{date.tm_year} {date.tm_mon}")
            cur.execute('INSERT INTO reading VALUES (NULL, ?, ?, ?, ?, ?, ?, ?)',
                        (file.stem, date.tm_year, date.tm_mon, row[1], row[2], row[3], row[4]))

# Create the rasters for each year and month
for year in range(2005, 2018):
    for month in range(5, 11):
        print(f"{year}-{month:02}")
        # Get all the data
        cur.execute(f'SELECT * FROM reading WHERE month = {month} AND year = {year}')
        data = cur.fetchall()
        # print(data)
        data_dic = {}
        for row in data:
            # print(row)
            # replace '' with None
            data_dic[row[1]] = {'precip': row[4] if row[4] != '' else None,
                                'temp': row[5] if row[5] != '' else None,
                                'humid': row[6] if row[6] != '' else None,
                                'wind': row[7] if row[7] != '' else None}
            if not row[4]:
                print(row[4])
                print(data_dic[row[1]]['precip'])
        # Open the weather station shapefile
        with fiona.open(str(station_shp), "r", driver="ESRI Shapefile") as in_shp:
            schema = in_shp.schema.copy()
            input_crs = in_shp.crs
            # Create a new weather station shapefile with the month's data
            with fiona.open(str(tmp_path / "weather_stations.shp"), "w", "ESRI Shapefile", schema, input_crs) as out_shp:
                for elem in in_shp:
                    if elem['properties']['name'] != 'placeholder':
                        # print(elem['properties']['name'], data_dic[elem['properties']['name']])
                        for weather_type in weather_types:
                            elem['properties'][weather_type] = data_dic[elem['properties']['name']][weather_type]
                    out_shp.write(
                        {'properties': elem['properties'], 'geometry': elem['geometry']})
        # Create a raster for each weather type
        for weather_type in weather_types:
            print(weather_type)
            subprocess.run(["gdal_grid",
                            "-zfield", weather_type,
                            "-a", "invdist:power=4",
                            "-outsize", "5000", "5000",
                            # '-txe', "200000.0", "564686.3972613546065986",
                            # '-tye', "6330438.8786582360044122", "6671762.7994462558999658",
                            # '-of', 'GTiff',
                            '-ot', 'Float32',
                            '-a_srs', 'EPSG:3400',
                            '--config', 'GDAL_NUM_THREADS', 'ALL_CPUS',
                            '-where', f'{weather_type} IS NOT NULL',
                            '-q',
                            str(tmp_path / "weather_stations.shp"), str(output_path / weather_type / f'{weather_type}_{year}-{month:02}.tif')],
                        )

# remove the temp dir
shutil.rmtree(tmp_path)

# The command to merge all the rasters, once the script is done
# This is run once over each subfolder with each datatype
# gdalwarp -multi -r average wind/*.tif wind.tif
