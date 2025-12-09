import rasterio
import numpy as np
from skimage.filters import threshold_otsu

# --- CONFIGURATION ---
FILE_NAME = "Sentinel2_Hebbal_Lake_2024.tif" 

# Band Mapping (Based on your GEE Export order: B3, B4, B8, B11, B5, B6)
B_GREEN = 1
B_RED   = 2
B_NIR   = 3
B_SWIR  = 4
B_RED_EDGE_1 = 5  
B_RED_EDGE_2 = 6  

def calculate_stats():
    print(f"--- PROCESSING: {FILE_NAME} ---")
    
    # 1. Load ALL Bands while the file is open
    try:
        with rasterio.open(FILE_NAME) as src:
            print("Image loaded successfully!")
            
            # Read bands and scale them
            green = src.read(B_GREEN) / 10000.0
            red   = src.read(B_RED)   / 10000.0
            nir   = src.read(B_NIR)   / 10000.0
            swir  = src.read(B_SWIR)  / 10000.0
            
            # --- MOVED UP: Read Red Edge bands here ---
            red_edge1 = src.read(B_RED_EDGE_1) / 10000.0
            red_edge2 = src.read(B_RED_EDGE_2) / 10000.0
            
            # Get pixel size
            transform = src.transform
            pixel_area_sqm = abs(transform.a * transform.e)
            
    except FileNotFoundError:
        print(f"ERROR: Could not find {FILE_NAME}.")
        return
    except IndexError:
        print("ERROR: Missing Bands! Did you re-run download_satellite.py with B5 and B6?")
        return

    # 2. Calculate MNDWI (Water Detection)
    mndwi = (green - swir) / (green + swir + 0.00001)
    
    # 3. Automatic Water Thresholding
    thresh = threshold_otsu(mndwi)
    water_mask = mndwi > thresh
    
    # 4. Calculate NDTI (Turbidity)
    ndti = (red - green) / (red + green + 0.00001)
    water_ndti = ndti[water_mask]
    
    # 5. Calculate Chlorophyll (NDCI)
    ndci = (red_edge1 - red) / (red_edge1 + red + 0.00001)
    water_ndci = ndci[water_mask]
    
    # 6. Calculate Algal Bloom (MCI)
    lam4, lam5, lam6 = 665.0, 705.0, 740.0
    continuum = red + ((red_edge2 - red) * ((lam5 - lam4) / (lam6 - lam4)))
    mci = red_edge1 - continuum
    water_mci = mci[water_mask]

    # 7. Statistics
    water_pixels_count = np.count_nonzero(water_mask)
    total_area_hectares = (water_pixels_count * pixel_area_sqm) / 10000.0
    
    avg_turbidity = np.mean(water_ndti)
    min_turbidity = np.min(water_ndti)
    max_turbidity = np.max(water_ndti)
    
    avg_chlorophyll = np.mean(water_ndci)
    avg_mci = np.mean(water_mci)

    # 8. Print Report
    print("\n" + "="*30)
    print("   LAKE HEALTH REPORT   ")
    print("="*30)
    print(f"Lake Area: {total_area_hectares:.2f} Hectares")
    print("-" * 30)
    print(f"Avg Turbidity (NDTI):   {avg_turbidity:.4f}")
    print(f"Avg Chlorophyll (NDCI): {avg_chlorophyll:.4f}")
    print(f"Algal Bloom Index (MCI):{avg_mci:.4f}")
    print("="*30)
    
    # Interpretation
    print("\nINTERPRETATION:")
    if avg_turbidity > 0.1:
        print("⚠️  High Turbidity (Sediment/Pollution)")
    else:
        print("✅  Water Clarity: Good")
        
    if avg_chlorophyll > 0.1:
        print("⚠️  High Algae Content (Eutrophication Risk)")
    else:
        print("✅  Algae Levels: Low")

if __name__ == "__main__":
    calculate_stats()