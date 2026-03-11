from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import rasterio
import numpy as np
from skimage.filters import threshold_otsu
from rasterio.warp import reproject, Resampling
from download_satellite import download_all
import os

app = FastAPI()

# Enable CORS so the Dashboard can talk to this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DYNAMIC CONFIGURATION ---
LAKE_CONFIG = {
    "hebbal": {
        "name": "Hebbal Lake",
        "sentinel": "Sentinel2_Hebbal_Lake_2024.tif",
        "landsat": "Landsat_Thermal_Hebbal_2024.tif",
        "coords": [77.5833, 13.0456] 
    },
    "bellandur": {
        "name": "Bellandur Lake",
        "sentinel": "Sentinel2_Bellandur_Lake_2024.tif",
        "landsat": "Landsat_Thermal_Bellandur_2024.tif",
        "coords": [77.666, 12.936] 
    },
    "ulsoor": {
        "name": "Ulsoor Lake",
        "sentinel": "Sentinel2_Ulsoor_Lake_2024.tif",
        "landsat": "Landsat_Thermal_Ulsoor_2024.tif",
        "coords": [77.622, 12.983]
    }
}

# Band Mapping (Matches your GEE Export)
B_GREEN = 1
B_RED   = 2
B_NIR   = 3
B_SWIR  = 4
B_RED_EDGE_1 = 5  
B_RED_EDGE_2 = 6  

@app.get("/update-satellite-data/{lake_id}")
def update_data(lake_id: str):
    if lake_id not in LAKE_CONFIG:
        return {"status": "error", "message": "Lake not found."}
        
    config = LAKE_CONFIG[lake_id]
    lake_name = config["name"]
    
    # Pass the specific coordinates and filenames to the downloader
    success = download_all(config["coords"], config["sentinel"], config["landsat"])
    
    if success:
        return {"status": "success", "message": f"Satellite data acquired for {lake_name}."}
    else:
        return {"status": "error", "message": "Download failed."}

@app.get("/analyze/{lake_id}")
def analyze_lake(lake_id: str):
    if lake_id not in LAKE_CONFIG:
        return {"error": "Target lake not found in database."}
        
    config = LAKE_CONFIG[lake_id]
    lake_name = config["name"]
    sentinel_path = config["sentinel"]
    landsat_path = config["landsat"]
    
    # Check if the files actually exist before trying to process them
    if not os.path.exists(sentinel_path) or not os.path.exists(landsat_path):
        return {"error": f"Satellite telemetry offline for {lake_name}. Files missing."}

    print(f"--- STARTING ANALYSIS FOR {lake_name.upper()} ---")

    # ---------------------------------------------------------
    # PART 1: SENTINEL-2 ANALYSIS (Visuals, Algae, Turbidity)
    # ---------------------------------------------------------
    try:
        with rasterio.open(sentinel_path) as src:
            # Capture metadata for Part 2
            sentinel_transform = src.transform
            sentinel_crs = src.crs
            sentinel_shape = src.shape
            pixel_area_sqm = abs(src.transform.a * src.transform.e)

            # Read Bands
            green = src.read(B_GREEN) / 10000.0
            red   = src.read(B_RED)   / 10000.0
            swir  = src.read(B_SWIR)  / 10000.0
            re1   = src.read(B_RED_EDGE_1) / 10000.0 
            re2   = src.read(B_RED_EDGE_2) / 10000.0 
            
            # --- 1. Water Mask (MNDWI) ---
            mndwi = (green - swir) / (green + swir + 0.00001)
            thresh = threshold_otsu(mndwi)
            water_mask = mndwi > thresh  # True = Water

            # --- 2. Indices ---
            ndti = (red - green) / (red + green + 0.00001)
            ndci = (re1 - red) / (re1 + red + 0.00001)
            
            # --- 3. MCI (Algal Bloom) ---
            lam4, lam5, lam6 = 665.0, 705.0, 740.0
            continuum = red + ((re2 - red) * ((lam5 - lam4) / (lam6 - lam4)))
            mci = re1 - continuum

            # --- 4. Statistics (Only calculate for Water Pixels) ---
            water_px = np.count_nonzero(water_mask)
            area_ha = (water_px * pixel_area_sqm) / 10000.0
            
            if water_px > 0:
                avg_turbidity = float(np.mean(ndti[water_mask]))
                avg_chlorophyll = float(np.mean(ndci[water_mask]))
                avg_mci = float(np.mean(mci[water_mask]))
            else:
                avg_turbidity, avg_chlorophyll, avg_mci = 0.0, 0.0, 0.0

    except Exception as e:
        return {"error": f"Sentinel Analysis Failed: {e}"}

    # ---------------------------------------------------------
    # PART 2: LANDSAT 9 FUSION (Accurate Temperature)
    # ---------------------------------------------------------
    avg_temp_c = 0.0
    try:
        with rasterio.open(landsat_path) as src_landsat:
            # 1. Read Raw Thermal Data
            st_band = src_landsat.read(1)
            
            # 2. Convert to Celsius
            kelvin = st_band * 0.00341802 + 149.0
            celsius_landsat = kelvin - 273.15
            
            # 3. RESAMPLE: Resize Landsat (30m) to match Sentinel (10m)
            celsius_resampled = np.zeros(sentinel_shape, dtype=np.float32)
            
            reproject(
                source=celsius_landsat,
                destination=celsius_resampled,
                src_transform=src_landsat.transform,
                src_crs=src_landsat.crs,
                dst_transform=sentinel_transform,
                dst_crs=sentinel_crs,
                resampling=Resampling.bilinear
            )
            
            # 4. FILTER: Use the Sentinel Water Mask
            if water_mask is not None:
                water_temps = celsius_resampled[water_mask]
                
                # Sanity Filter: Remove errors (-50) and Land (>35)
                # Note: If lake is genuinely boiling (>35), adjust this cap.
                # For now, <35 prevents "road heat" from ruining the average.
                valid_temps = water_temps[(water_temps > 0) & (water_temps < 35)]
                
                if len(valid_temps) > 0:
                    avg_temp_c = float(np.mean(valid_temps))
                else:
                    avg_temp_c = 0.0

    except Exception as e:
        print(f"Landsat Warning: {e}") 

    # ---------------------------------------------------------
    # PART 3: FORMAT RESPONSE FOR DASHBOARD
    # ---------------------------------------------------------
    status = "Moderate"
    conclusion = "Analysis pending."

    # --- DYNAMIC INSIGHTS ENGINE ---
    if avg_chlorophyll > 0.1:
        status = "High Algae Risk"
        
        # Custom insight for Bellandur's specific history
        if lake_name == "Bellandur Lake":
            conclusion = f"Severe eutrophication (NDCI: {avg_chlorophyll:.3f}). Bellandur's historical nutrient loading combined with {avg_temp_c:.1f}°C surface temp is fueling rapid algal blooms. Immediate aeration recommended."
        
        # Insight if both Temp and Algae are high
        elif avg_temp_c > 30.0:
            conclusion = f"Thermal anomaly ({avg_temp_c:.1f}°C) detected alongside high chlorophyll. Warm water is actively accelerating algal reproduction. Suspected cause: Urban heat island effect & sewage inflow."
        
        # Insight if Turbidity and Algae are high
        elif avg_turbidity > 0.05:
            conclusion = f"High biological activity (NDCI: {avg_chlorophyll:.3f}) coupled with elevated turbidity. Indicates heavy suspended particulate matter and dangerous nutrient runoff."
        
        # Fallback for standard high algae
        else:
            conclusion = f"Chlorophyll levels exceed safe thresholds (NDCI: {avg_chlorophyll:.3f}). Regular monitoring required to prevent full-scale eutrophication."

    elif avg_turbidity > 0.1:
        status = "High Turbidity"
        conclusion = f"Elevated turbidity levels detected (NDTI: {avg_turbidity:.3f}). Water clarity is significantly compromised, likely due to recent urban runoff or unchecked sediment discharge."

    else:
        status = "Clear"
        conclusion = f"Lake parameters are within normal thresholds. Surface temperature is stable at {avg_temp_c:.1f}°C with negligible biological hazard."

    print(f"Analysis Complete. Temp: {avg_temp_c}")

    return {
        "lake_name": lake_name,
        "area_hectares": round(area_ha, 2),
        "avg_ndti": round(avg_turbidity, 4),
        "avg_ndci": round(avg_chlorophyll, 4),
        "avg_mci": round(avg_mci, 4),
        "avg_lst": round(avg_temp_c, 1),
        "status": status,
        "conclusion": conclusion,
        "data_source": "Sentinel-2 & Landsat-9 (Fused)"
    }