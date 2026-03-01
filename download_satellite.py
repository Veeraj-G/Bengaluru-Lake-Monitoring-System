import ee
import requests
import os

# --- CONFIGURATION ---
# Use your specific Project ID
PROJECT_ID = 'final-year-project-477507' 
# ROI_POINT = [77.5833, 13.0456] # Hebbal Lake

def init_gee():
    try:
        ee.Initialize(project=PROJECT_ID)
        return True
    except:
        print("Failed to connect to GEE.")
        return False

def download_sentinel_image(roi_point, filename):
    print(f"Searching for Sentinel-2 data at {roi_point}...")
    roi = ee.Geometry.Point(roi_point).buffer(1500).bounds()
    
    collection = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                  .filterBounds(roi)
                  .filterDate('2024-01-01', '2024-12-31')
                  .sort('CLOUDY_PIXEL_PERCENTAGE')
                  .select(['B3', 'B4', 'B8', 'B11', 'B5', 'B6']))

    image = collection.first()
    url = image.getDownloadURL({
        'scale': 10, 'crs': 'EPSG:32643', 'region': roi,
        'filePerBand': False, 'format': 'GEO_TIFF'
    })
    return save_file(url, filename)

def download_landsat_thermal(roi_point, filename):
    print(f"Searching for Landsat 9 data at {roi_point}...")
    roi = ee.Geometry.Point(roi_point).buffer(1500).bounds()

    collection = (ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
                  .filterBounds(roi)
                  .filterDate('2024-01-01', '2024-12-31')
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
        print(f"Downloading {filename}...")
        response = requests.get(url)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                f.write(response.content)
            print("Download Complete.")
            return True
        else:
            print("HTTP Error.")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def download_all(roi_point, sentinel_file, landsat_file):
    if init_gee():
        s1 = download_sentinel_image(roi_point, sentinel_file)
        s2 = download_landsat_thermal(roi_point, landsat_file)
        return s1 and s2
    return False

if __name__ == "__main__":
    download_all()