import ee
import requests
import os
import zipfile
import io
from datetime import datetime, timedelta

# --- CONFIGURATION ---
# Use your specific Project ID
PROJECT_ID = 'final-year-project-477507' 

def init_gee():
    try:
        ee.Initialize(project=PROJECT_ID)
        return True
    except:
        print("Failed to connect to GEE. Please authenticate.")
        return False

def get_dynamic_dates():
    """Temporarily hardcoded to pull historical 2024 data for the presentation."""
    # To go back to live data later, just uncomment the next two lines:
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    # Use these specific dates for the "Time Machine" demonstration:
    # start_date = '2023-09-01'
    # end_date = '2023-10-31' # Post-monsoon, usually clear skies and full lakes
    return start_date, end_date

def download_sentinel_image(roi_point, filename):
    print(f"Searching for LIVE Sentinel-2 data at {roi_point}...")
    roi = ee.Geometry.Point(roi_point).buffer(1500).bounds()
    
    start_date, end_date = get_dynamic_dates()
    print(f"Scanning dates: {start_date} to {end_date}")

    collection = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                  .filterBounds(roi)
                  .filterDate(start_date, end_date)
                  .sort('CLOUDY_PIXEL_PERCENTAGE')
                  .select(['B3', 'B4', 'B8', 'B11', 'B5', 'B6']))

    image = collection.first()
    url = image.getDownloadURL({
        'scale': 10, 'crs': 'EPSG:32643', 'region': roi,
        'filePerBand': False, 'format': 'GEO_TIFF'
    })
    return save_file(url, filename)

def download_landsat_thermal(roi_point, filename):
    print(f"Searching for LIVE Landsat 9 data at {roi_point}...")
    roi = ee.Geometry.Point(roi_point).buffer(1500).bounds()

    start_date, end_date = get_dynamic_dates()

    collection = (ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
                  .filterBounds(roi)
                  .filterDate(start_date, end_date)
                  .sort('CLOUD_COVER')
                  .select(['ST_B10'])) 

    image = collection.first()
    url = image.getDownloadURL({
        'scale': 30, 'crs': 'EPSG:32643', 'region': roi,
        'filePerBand': False, 'format': 'GEO_TIFF'
    })
    return save_file(url, filename)

def save_file(url, filename):
    try:
        print(f"Downloading -> {filename}")
        response = requests.get(url)
        if response.status_code == 200:
            # GEE is sending the raw .tif directly! Just save it.
            with open(filename, 'wb') as f:
                f.write(response.content)
            print("Download Complete.")
            return True
        else:
            print(f"HTTP Error: {response.status_code}")
            print(response.text) # Prints the exact GEE error if it fails
            return False
    except Exception as e:
        print(f"Error saving file: {e}")
        return False

def download_all(roi_point, sentinel_file, landsat_file):
    if init_gee():
        s1 = download_sentinel_image(roi_point, sentinel_file)
        s2 = download_landsat_thermal(roi_point, landsat_file)
        return s1 and s2
    return False