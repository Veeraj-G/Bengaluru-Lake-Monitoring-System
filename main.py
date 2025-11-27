from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import rasterio
import numpy as np
from skimage.filters import threshold_otsu

# --- IMPORT THE DOWNLOADER ---
from download_satellite import download_latest_image

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FILE_NAME = "Sentinel2_Hebbal_Lake_2024.tif"
B_GREEN, B_RED, B_NIR, B_SWIR = 1, 2, 3, 4

@app.get("/")
def read_root():
    return {"message": "Bengaluru Lake Monitoring API is Online!"}

# --- NEW ENDPOINT: TRIGGER DOWNLOAD ---
@app.get("/update-satellite-data")
def update_data():
    success = download_latest_image()
    if success:
        return {"status": "success", "message": "Latest satellite image downloaded successfully."}
    else:
        return {"status": "error", "message": "Failed to download image from Google Earth Engine."}

@app.get("/analyze/hebbal")
def analyze_hebbal():
    try:
        with rasterio.open(FILE_NAME) as src:
            green = src.read(B_GREEN) / 10000.0
            red   = src.read(B_RED)   / 10000.0
            swir  = src.read(B_SWIR)  / 10000.0
            transform = src.transform
            pixel_area_sqm = abs(transform.a * transform.e)
    except Exception:
        return {"error": "Satellite image not found. Please click 'Fetch Data'."}

    # Calculations
    mndwi = (green - swir) / (green + swir + 0.00001)
    thresh = threshold_otsu(mndwi)
    water_mask = mndwi > thresh

    ndti = (red - green) / (red + green + 0.00001)
    water_ndti = ndti[water_mask]

    water_pixels = np.count_nonzero(water_mask)
    area_ha = (water_pixels * pixel_area_sqm) / 10000.0
    
    # Handle case where no water is detected
    if water_pixels > 0:
        avg_turbidity = float(np.mean(water_ndti))
    else:
        avg_turbidity = 0.0

    status = "Moderate"
    if avg_turbidity > 0.1: status = "High Turbidity (Polluted)"
    if avg_turbidity < -0.1: status = "Clear"

    return {
        "lake_name": "Hebbal Lake",
        "area_hectares": round(area_ha, 2),
        "avg_ndti": round(avg_turbidity, 4),
        "status": status,
        "data_source": "Sentinel-2 Satellite (Live)"
    }