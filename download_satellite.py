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
        # 1. Initialize GEE
        try:
            ee.Initialize(project='final-year-project-477507')
            print("Successfully connected to Google Earth Engine.")
        except Exception:
            print("Failed to connect to GEE.")
            return False

        # 2. Define the Target (Hebbal Lake)
        roi = ee.Geometry.Point([77.5833, 13.0456]).buffer(1500).bounds()

        # 3. Find the Best Image
        print("Searching for clear satellite images...")
        collection = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                      .filterBounds(roi)
                      .filterDate('2024-01-01', '2024-12-31')
                      .sort('CLOUDY_PIXEL_PERCENTAGE')
                      .select(['B3', 'B4', 'B8', 'B11']))

        image = collection.first()
        
        # 4. Generate URL
        url = image.getDownloadURL({
            'scale': 10,
            'crs': 'EPSG:32643', # Metric CRS
            'region': roi,
            'filePerBand': False,
            'format': 'GEO_TIFF'
        })

        # 5. Download
        output_file = "Sentinel2_Hebbal_Lake_2024.tif"
        print(f"Downloading to {output_file}...")
        
        response = requests.get(url)

        if response.status_code == 200:
            content = response.content
            
            # Handle ZIP
            if content.startswith(b'PK'):
                with zipfile.ZipFile(io.BytesIO(content)) as zip_ref:
                    for file in zip_ref.namelist():
                        if file.endswith(".tif"):
                            zip_ref.extract(file, ".")
                            if os.path.exists(output_file):
                                os.remove(output_file)
                            os.rename(file, output_file)
                            return True
            
            # Handle Raw TIFF
            elif content.startswith(b'II') or content.startswith(b'MM'):
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

# This allows you to still run it manually if you want
if __name__ == "__main__":
    download_latest_image()