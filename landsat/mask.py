#!/usr/bin/env python3
"""
GEOG*4480 W19
Isaac Wismer
wismeri@uoguelph.ca

Created for a project on wildfire vulnerability in McKenzie County in Alberta

This script extracts all the images from a landsat order, and removes all the
pixels from the images that are not clear according to the QA band.

Run with:
./mask.py dir/of/order/
"""

import tarfile
from pathlib import *
import sys
import subprocess
import shutil

# Get the directory containing the downloaded order
cwd = Path(sys.argv[1])

for f in cwd.iterdir():
    # Ignore anything that isn't a tar.gz file
    if f.is_dir() or f.suffix != ".gz":
        continue
    # Create a directory to extract to
    extract_path = Path(cwd / f.stem)
    extract_path.mkdir(exist_ok=True)
    # Extract the file to the extract directory
    with tarfile.open(f, mode='r') as tar:
        print(f"Extracting: {f.name}")
        tar.extractall(path=extract_path)
    tifs = {}
    # Loop over the tif files in the extract dir
    for tif in extract_path.iterdir():
        if tif.suffix == '.tif':
            # Get the QA and ndmi images
            if "pixel_qa" in tif.name:
                tifs['pixel_qa'] = tif
            elif "sr_ndmi" in tif.name:
                tifs['sr_ndmi'] = tif
    # Create the paths for output
    output_file = str(tifs['sr_ndmi'].stem) + "_mask.tif"
    output_path = Path(cwd / "output" / output_file)

    print(f"Running Raster Calculator: {output_file}")
    # Run GDAL raster calculator to remove pixels that are not clear
    subprocess.run(["gdal_calc.py",
                    "-A", tifs["sr_ndmi"],
                    "-B", tifs["pixel_qa"],
                    "--outfile", output_path,
                    '--calc', "select([(B == 66) | (B == 132), (B < 66) | (B > 132), (B > 66) & (B < 132)], [A, -9999, -9999])"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    # Delete the extracted files
    shutil.rmtree(extract_path)
