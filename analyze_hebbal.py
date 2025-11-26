import rasterio
import numpy as np
from skimage.filters import threshold_otsu

# --- CONFIGURATION ---
# This matches the filename you downloaded
FILE_NAME = "Sentinel2_Hebbal_Lake_2024.tif" 

# Band Mapping (Based on your GEE Export order: B3, B4, B8, B11)
# Python uses 1-based indexing for bands
B_GREEN = 1
B_RED   = 2
B_NIR   = 3
B_SWIR  = 4

def calculate_stats():
    print(f"--- PROCESSING: {FILE_NAME} ---")
    
    # 1. Load the Image
    try:
        with rasterio.open(FILE_NAME) as src:
            print("Image loaded successfully!")
            
            # Read bands and scale them (Sentinel-2 is scaled by 10000)
            green = src.read(B_GREEN) / 10000.0
            red   = src.read(B_RED)   / 10000.0
            nir   = src.read(B_NIR)   / 10000.0
            swir  = src.read(B_SWIR)  / 10000.0
            
            # Get pixel size for area calc
            transform = src.transform
            pixel_area_sqm = abs(transform.a * transform.e) # Width * Height
            
    except FileNotFoundError:
        print(f"ERROR: Could not find {FILE_NAME}. Make sure it is in the same folder!")
        return

    # 2. Calculate MNDWI (Water Detection)
    # Formula: (Green - SWIR) / (Green + SWIR)
    # We add 0.00001 to avoid division by zero errors
    mndwi = (green - swir) / (green + swir + 0.00001)
    
    # 3. Automatic Water Thresholding (Otsu's Method)
    # This finds the best cutoff number to separate "Water" from "Land" automatically
    thresh = threshold_otsu(mndwi)
    water_mask = mndwi > thresh
    
    # 4. Calculate NDTI (Turbidity) ONLY on Water pixels
    # Formula: (Red - Green) / (Red + Green)
    ndti = (red - green) / (red + green + 0.00001)
    
    # Filter NDTI to only show water pixels
    water_ndti = ndti[water_mask]
    
    # 5. Calculate Statistics
    water_pixels_count = np.count_nonzero(water_mask)
    total_area_hectares = (water_pixels_count * pixel_area_sqm) / 10000.0
    
    avg_turbidity = np.mean(water_ndti)
    min_turbidity = np.min(water_ndti)
    max_turbidity = np.max(water_ndti)

    # 6. Print the Report
    print("\n" + "="*30)
    print("   LAKE HEALTH REPORT   ")
    print("="*30)
    print(f"Lake Area (Detected): {total_area_hectares:.2f} Hectares")
    print("-" * 30)
    print(f"Average NDTI (Turbidity): {avg_turbidity:.4f}")
    print(f"Min NDTI: {min_turbidity:.4f}")
    print(f"Max NDTI: {max_turbidity:.4f}")
    print("="*30)
    
    # Interpretation
    print("\nINTERPRETATION:")
    if avg_turbidity > 0.1:
        print("⚠️  High Turbidity Detected (Possible Sediment/Pollution)")
    elif avg_turbidity < -0.1:
        print("✅  Water appears relatively clear")
    else:
        print("ℹ️  Moderate Turbidity")

if __name__ == "__main__":
    calculate_stats()