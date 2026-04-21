from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import rasterio
import numpy as np
from skimage.filters import threshold_otsu
from rasterio.warp import reproject, Resampling
from download_satellite import download_all
import os

from fastapi.responses import FileResponse
from report_generator import create_pdf_report

app = FastAPI()

# Enable CORS so the Dashboard can talk to this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DYNAMIC CONFIGURATION (10-LAKE CITY-WIDE DEPLOYMENT) ---
LAKE_CONFIG = {
    "hebbal": {
        "name": "Hebbal Lake",
        "sentinel": "Sentinel2_Hebbal_Lake_2026.tif",
        "landsat": "Landsat_Thermal_Hebbal_2026.tif",
        "coords": [77.5833, 13.0456] 
    },
    "bellandur": {
        "name": "Bellandur Lake",
        "sentinel": "Sentinel2_Bellandur_Lake_2026.tif",
        "landsat": "Landsat_Thermal_Bellandur_2026.tif",
        "coords": [77.6660, 12.9360] 
    },
    "ulsoor": {
        "name": "Ulsoor Lake",
        "sentinel": "Sentinel2_Ulsoor_Lake_2026.tif",
        "landsat": "Landsat_Thermal_Ulsoor_2026.tif",
        "coords": [77.6220, 12.9830]
    },
    "varthur": {
        "name": "Varthur Lake",
        "sentinel": "Sentinel2_Varthur_Lake_2026.tif",
        "landsat": "Landsat_Thermal_Varthur_2026.tif",
        "coords": [77.7300, 12.9400]
    },
    "madiwala": {
        "name": "Madiwala Lake",
        "sentinel": "Sentinel2_Madiwala_Lake_2026.tif",
        "landsat": "Landsat_Thermal_Madiwala_2026.tif",
        "coords": [77.6180, 12.9150]
    },
    "jakkur": {
        "name": "Jakkur Lake",
        "sentinel": "Sentinel2_Jakkur_Lake_2026.tif",
        "landsat": "Landsat_Thermal_Jakkur_2026.tif",
        "coords": [77.6050, 13.0760]
    },
    "sankey": {
        "name": "Sankey Tank",
        "sentinel": "Sentinel2_Sankey_Tank_2026.tif",
        "landsat": "Landsat_Thermal_Sankey_2026.tif",
        "coords": [77.5750, 13.0080]
    },
    "agara": {
        "name": "Agara Lake",
        "sentinel": "Sentinel2_Agara_Lake_2026.tif",
        "landsat": "Landsat_Thermal_Agara_2026.tif",
        "coords": [77.6440, 12.9230]
    },
    "yelahanka": {
        "name": "Yelahanka Lake",
        "sentinel": "Sentinel2_Yelahanka_Lake_2026.tif",
        "landsat": "Landsat_Thermal_Yelahanka_2026.tif",
        "coords": [77.5950, 13.1000]
    },
    "nagavara": {
        "name": "Nagavara Lake",
        "sentinel": "Sentinel2_Nagavara_Lake_2026.tif",
        "landsat": "Landsat_Thermal_Nagavara_2026.tif",
        "coords": [77.6200, 13.0400]
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
        return {"error": "Lake not found."}
        
    config = LAKE_CONFIG[lake_id]
    
    # 1. Dynamically pull the year from your Time Machine script
    from download_satellite import get_dynamic_dates, download_all
    _, end_date = get_dynamic_dates()
    current_year = end_date.split('-')[0] # Extracts "2024" or "2026"
    
    # 2. Swap out the hardcoded "2026" for the dynamic year
    sentinel_path = config["sentinel"].replace("2026", current_year)
    landsat_path = config["landsat"].replace("2026", current_year)
    
    success = download_all(config["coords"], sentinel_path, landsat_path)
    if success:
        return {"status": "success", "message": f"Data acquired for {config['name']}."}
    return {"status": "error", "message": "Download failed."}

@app.get("/analyze/{lake_id}")
def analyze_lake(lake_id: str):
    if lake_id not in LAKE_CONFIG:
        return {"error": "Target lake not found in database."}
        
    config = LAKE_CONFIG[lake_id]
    lake_name = config["name"]
    
    # 1. Dynamically pull the year to find the correct file
    from download_satellite import get_dynamic_dates
    _, end_date = get_dynamic_dates()
    current_year = end_date.split('-')[0]
    
    # 2. Assign the dynamic paths
    sentinel_path = config["sentinel"].replace("2026", current_year)
    landsat_path = config["landsat"].replace("2026", current_year)
    
    if not os.path.exists(sentinel_path) or not os.path.exists(landsat_path):
        return {"error": f"Satellite telemetry offline for {lake_name} ({current_year}). Files missing."}
    
    # ---------------------------------------------------------
    # PART 1: SENTINEL-2 ANALYSIS (Clean Math)
    # ---------------------------------------------------------
    try:
        with rasterio.open(sentinel_path) as src:
            sentinel_transform = src.transform
            sentinel_crs = src.crs
            sentinel_shape = src.shape
            pixel_area_sqm = 100.0  

            green = src.read(B_GREEN).astype('float32') / 10000.0
            red   = src.read(B_RED).astype('float32') / 10000.0
            swir  = src.read(B_SWIR).astype('float32') / 10000.0
            re1   = src.read(B_RED_EDGE_1).astype('float32') / 10000.0
            re2   = src.read(B_RED_EDGE_2).astype('float32') / 10000.0
            
            np.seterr(divide='ignore', invalid='ignore')
            
            # Strict boundary to ignore black edges
            valid_data = (green > 0.0001) & (swir > 0.0001)
            
            green = np.where(valid_data, green, np.nan)
            red   = np.where(valid_data, red, np.nan)
            swir  = np.where(valid_data, swir, np.nan)
            re1   = np.where(valid_data, re1, np.nan)
            re2   = np.where(valid_data, re2, np.nan)
            
            # Water Mask: Very strict to only grab actual water
            mndwi = (green - swir) / (green + swir + 1e-8)
            water_mask = (mndwi > 0.1) & valid_data

            # Indices
            ndti = (red - green) / (red + green + 1e-8)
            ndci = (re1 - red) / (re1 + red + 1e-8)
            
            # MCI
            lam4, lam5, lam6 = 665.0, 705.0, 740.0
            continuum = red + ((re2 - red) * ((lam5 - lam4) / (lam6 - lam4)))
            mci = re1 - continuum

            # Area Calculation
            water_px = np.count_nonzero(water_mask)
            area_ha = (water_px * pixel_area_sqm) / 10000.0
            
            # Use Medians for ultimate stability against bad pixels
            if water_px > 0:
                avg_turbidity = float(np.nanmedian(ndti[water_mask]))
                avg_chlorophyll = float(np.nanmedian(ndci[water_mask]))
                avg_mci = float(np.nanmedian(mci[water_mask]))
            else:
                avg_turbidity, avg_chlorophyll, avg_mci = 0.0, 0.0, 0.0

    except Exception as e:
        return {"error": f"Sentinel Analysis Failed: {e}"}

    # ---------------------------------------------------------
    # PART 2: LANDSAT 9 FUSION
    # ---------------------------------------------------------
    avg_temp_c = 0.0
    try:
        with rasterio.open(landsat_path) as src_landsat:
            st_band = src_landsat.read(1).astype('float32')
            
            valid_thermal = st_band > 0
            kelvin = np.where(valid_thermal, (st_band * 0.00341802) + 149.0, np.nan)
            celsius_landsat = kelvin - 273.15
            
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
            
            if water_mask is not None:
                water_temps = celsius_resampled[water_mask]
                valid_temps = water_temps[(water_temps >= 15.0) & (water_temps <= 45.0)]
                
                if len(valid_temps) > 5:
                    avg_temp_c = float(np.nanmedian(valid_temps))
                else:
                    avg_temp_c = 28.5

    except Exception as e:
        print(f"Landsat Warning: {e}") 

    # ---------------------------------------------------------
    # PART 3: PROFESSIONAL INSIGHTS ENGINE
    # ---------------------------------------------------------
    status = "Monitoring"
    conclusion = "Awaiting cross-parameter analysis."

    if avg_chlorophyll > 0.08:
        status = "Elevated Algae Risk"
        conclusion = f"Biological indicators (NDCI: {avg_chlorophyll:.3f}) show significant algal presence. "
        if avg_temp_c > 30.0:
            conclusion += f"The current surface temperature of {avg_temp_c:.1f}°C is actively accelerating this growth."
        else:
            conclusion += "Continuous monitoring is advised to prevent further degradation."
            
    elif avg_turbidity > 0.05:
        status = "High Turbidity"
        conclusion = f"Water clarity is compromised (NDTI: {avg_turbidity:.3f}) due to high levels of suspended particulate matter. "
        if area_ha < 15.0:
            conclusion += "Given the reduced surface area, this likely indicates active desilting work or severe seasonal drying rather than standard runoff."
        else:
            conclusion += "This suggests recent urban runoff or sediment disturbance."
            
    elif avg_temp_c > 31.0:
        status = "Thermal Anomaly"
        conclusion = f"The surface temperature is notably high ({avg_temp_c:.1f}°C), though biological parameters remain stable. This may indicate an Urban Heat Island effect."
        
    else:
        status = "Stable"
        conclusion = f"Current optical and thermal telemetry indicate the water body is operating within standard ecological thresholds. Temperature remains stable at {avg_temp_c:.1f}°C."

    # Specific context for Bellandur
    if lake_name == "Bellandur Lake" and status != "Stable":
        conclusion += " Note: Historical nutrient loading in the Bellandur catchment frequently exacerbates these conditions."

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

@app.get("/api/download-report")
async def download_report(lake_name: str, area: float, ndci: float, lst: float, ndti: float, mci: float, status: str, conclusion: str):
    """Generates the PDF and sends it to the user's browser."""
    # We pass the new variables into the generator
    pdf_file = create_pdf_report(lake_name, area, ndci, lst, ndti, mci, status, conclusion)
    
    return FileResponse(
        path=pdf_file, 
        filename=f"{lake_name}_Telemetry_Report.pdf", 
        media_type='application/pdf'
    )