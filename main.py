from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import rasterio
import numpy as np
from skimage.filters import threshold_otsu
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
B_RED_EDGE_1, B_RED_EDGE_2 = 5, 6

@app.get("/")
def read_root():
    return {"message": "Bengaluru Lake Monitoring API is Online!"}

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
            red_edge1 = src.read(B_RED_EDGE_1) / 10000.0
            red_edge2 = src.read(B_RED_EDGE_2) / 10000.0
            transform = src.transform
            pixel_area_sqm = abs(transform.a * transform.e)
    except Exception:
        return {"error": "Satellite image not found. Please click 'Fetch Data'."}

    # Calculations
    mndwi = (green - swir) / (green + swir + 0.00001)
    try:
        thresh = threshold_otsu(mndwi)
        water_mask = mndwi > thresh
    except:
        return {"error": "Could not detect water."}

    ndti = (red - green) / (red + green + 0.00001)
    water_ndti = ndti[water_mask]

    ndci = (red_edge1 - red) / (red_edge1 + red + 0.00001)
    water_ndci = ndci[water_mask]

    # Calculate MCI
    lam4, lam5, lam6 = 665.0, 705.0, 740.0
    continuum = red + ((red_edge2 - red) * ((lam5 - lam4) / (lam6 - lam4)))
    mci = red_edge1 - continuum
    water_mci = mci[water_mask]

    # Stats
    water_pixels = np.count_nonzero(water_mask)
    area_ha = (water_pixels * pixel_area_sqm) / 10000.0
    
    avg_turbidity = float(np.mean(water_ndti)) if water_pixels > 0 else 0.0
    avg_chlorophyll = float(np.mean(water_ndci)) if water_pixels > 0 else 0.0
    avg_mci = float(np.mean(water_mci)) if water_pixels > 0 else 0.0

    # --- NEW: GENERATE CONCLUSION / INSIGHT ---
    # This logic matrix decides the story based on the numbers
    
    conclusion = "Analysis complete."
    status = "Moderate"

    # SCENARIO 1: High Algae + Low Turbidity (Current Hebbal Scenario)
    if avg_chlorophyll > 0.1 and avg_turbidity < 0.1:
        status = "High Algae Risk"
        conclusion = (
            "The water appears physically clear (Low Turbidity) but has high biological activity. "
            "This suggests an inflow of dissolved nutrients, likely from 'Untreated Sewage', "
            "feeding an algal bloom."
        )

    # SCENARIO 2: High Turbidity + Low Algae
    elif avg_chlorophyll < 0.1 and avg_turbidity > 0.1:
        status = "High Turbidity"
        conclusion = (
            "The water is muddy and opaque (High Sediment). "
            "Since algae levels are low, this is likely caused by **Physical Runoff** "
            "from recent rainfall or nearby construction debris."
        )

    # SCENARIO 3: High Algae + High Turbidity
    elif avg_chlorophyll > 0.1 and avg_turbidity > 0.1:
        status = "Critical Pollution"
        conclusion = (
            "Critical Condition detected. The lake suffers from both heavy sediment load "
            "and severe eutrophication. Immediate intervention is recommended."
        )

    # SCENARIO 4: Clear
    elif avg_chlorophyll <= 0.1 and avg_turbidity <= 0.1:
        status = "Clear"
        conclusion = (
            "The lake appears healthy. Both sediment levels and biological activity "
            "are within safe limits."
        )

    return {
        "lake_name": "Hebbal Lake",
        "area_hectares": round(area_ha, 2),
        "avg_ndti": round(avg_turbidity, 4),
        "avg_ndci": round(avg_chlorophyll, 4),
        "avg_mci": round(avg_mci, 4),
        "status": status,
        "conclusion": conclusion,  # Sending this to frontend
        "data_source": "Sentinel-2 Satellite (Live)"
    }