import ee
import requests
import os
import zipfile
import io

def download_latest_image():
    """
    Connects to GEE, finds the best 2024 image, and downloads it.
    Returns True if successful, False otherwise.
    """
    try:
        try:
            ee.Initialize(project='final-year-project-477507')
            print("Successfully connected to Google Earth Engine.")
        except Exception:
            print("Failed to connect to GEE.")
            return False

        roi = ee.Geometry.Point([77.5833, 13.0456]).buffer(1500).bounds()

        print("Searching for clear satellite images...")
        collection = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                      .filterBounds(roi)
                      .filterDate('2024-01-01', '2024-12-31')
                      .sort('CLOUDY_PIXEL_PERCENTAGE')
                      # UPDATED: Added B5 and B6 for Chlorophyll
                      .select(['B3', 'B4', 'B8', 'B11', 'B5', 'B6']))

        image = collection.first()
        
        url = image.getDownloadURL({
            'scale': 10,
            'crs': 'EPSG:32643', 
            'region': roi,
            'filePerBand': False,
            'format': 'GEO_TIFF'
        })

        output_file = "Sentinel2_Hebbal_Lake_2024.tif"
        print(f"Downloading to {output_file}...")
        
        response = requests.get(url)

        if response.status_code == 200:
            content = response.content
            if content.startswith(b'II') or content.startswith(b'MM'):
                with open(output_file, 'wb') as f:
                    f.write(content)
                return True
            else:
                print("Error: Download format unrecognized.")
                return False
        else:
            print("HTTP Error from Google.")
            return False

    except Exception as e:
        print(f"An error occurred: {e}")
        return False

if __name__ == "__main__":
    download_latest_image()