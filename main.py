from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import rasterio
import numpy as np
from skimage.filters import threshold_otsu
from rasterio.warp import reproject, Resampling  # <--- NEW IMPORT
from download_satellite import download_all

app = FastAPI()

# Enable CORS so the Dashboard can talk to this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURATION ---
SENTINEL_FILE = "Sentinel2_Hebbal_Lake_2024.tif"
LANDSAT_FILE = "Landsat_Thermal_Hebbal_2024.tif"

# Band Mapping (Matches your GEE Export)
B_GREEN = 1
B_RED   = 2
B_NIR   = 3
B_SWIR  = 4
B_RED_EDGE_1 = 5  
B_RED_EDGE_2 = 6  

@app.get("/update-satellite-data")
def update_data():
    """Button to re-download fresh data from GEE"""
    success = download_all()
    if success:
        return {"status": "success", "message": "Sentinel-2 and Landsat-9 data downloaded."}
    else:
        return {"status": "error", "message": "Download failed."}

@app.get("/analyze/hebbal")
def analyze_hebbal():
    print("--- STARTING ANALYSIS ---")
    
    # Variables to hold Sentinel metadata for alignment
    sentinel_transform = None
    sentinel_crs = None
    sentinel_shape = None
    water_mask = None

    # ---------------------------------------------------------
    # PART 1: SENTINEL-2 ANALYSIS (Visuals, Algae, Turbidity)
    # ---------------------------------------------------------
    try:
        with rasterio.open(SENTINEL_FILE) as src:
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
        with rasterio.open(LANDSAT_FILE) as src_landsat:
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

    if avg_chlorophyll > 0.1:
        status = "High Algae Risk"
        conclusion = (
            f"High biological activity detected (NDCI: {avg_chlorophyll:.3f}). "
            f"Surface temperature is <b>{avg_temp_c:.1f}°C</b>. "
            "Warm water accelerates algae growth. Likely cause: Sewage inflow."
        )
    elif avg_turbidity > 0.1:
        status = "High Turbidity"
        conclusion = "Water contains high sediment/mud levels. Likely due to runoff."
    else:
        status = "Clear"
        conclusion = f"Lake health is stable. Surface temperature is normal at <b>{avg_temp_c:.1f}°C</b>."

    print(f"Analysis Complete. Temp: {avg_temp_c}")

    return {
        "lake_name": "Hebbal Lake",
        "area_hectares": round(area_ha, 2),
        "avg_ndti": round(avg_turbidity, 4),
        "avg_ndci": round(avg_chlorophyll, 4),
        "avg_mci": round(avg_mci, 4),
        "avg_lst": round(avg_temp_c, 1),
        "status": status,
        "conclusion": conclusion,
        "data_source": "Sentinel-2 & Landsat-9 (Fused)"
    }