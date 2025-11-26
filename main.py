from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # <--- NEW IMPORT
import rasterio
import numpy as np
from skimage.filters import threshold_otsu

app = FastAPI()

# --- NEW: ENABLE CORS ---
# This tells the server: "Allow any website to request data from me"
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (files, localhost, etc.)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

# Configuration
FILE_NAME = "Sentinel2_Hebbal_Lake_2024.tif"
B_GREEN, B_RED, B_NIR, B_SWIR = 1, 2, 3, 4

@app.get("/")
def read_root():
    return {"message": "Bengaluru Lake Monitoring API is Online!"}

@app.get("/analyze/hebbal")
def analyze_hebbal():
    # 1. Load Image
    try:
        with rasterio.open(FILE_NAME) as src:
            green = src.read(B_GREEN) / 10000.0
            red   = src.read(B_RED)   / 10000.0
            swir  = src.read(B_SWIR)  / 10000.0
            transform = src.transform
            pixel_area_sqm = abs(transform.a * transform.e)
    except Exception as e:
        return {"error": "Could not find satellite image. Check file path."}

    # 2. Water Detection (MNDWI)
    mndwi = (green - swir) / (green + swir + 0.00001)
    thresh = threshold_otsu(mndwi)
    water_mask = mndwi > thresh

    # 3. Turbidity (NDTI)
    ndti = (red - green) / (red + green + 0.00001)
    water_ndti = ndti[water_mask]

    # 4. Calculate Stats
    water_pixels = np.count_nonzero(water_mask)
    area_ha = (water_pixels * pixel_area_sqm) / 10000.0
    avg_turbidity = float(np.mean(water_ndti))

    # 5. Determine Status
    status = "Moderate"
    if avg_turbidity > 0.1: status = "High Turbidity (Polluted)"
    if avg_turbidity < -0.1: status = "Clear"

    # 6. Return JSON
    return {
        "lake_name": "Hebbal Lake",
        "area_hectares": round(area_ha, 2),
        "avg_ndti": round(avg_turbidity, 4),
        "status": status,
        "data_source": "Sentinel-2 Satellite"
    }