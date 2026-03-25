import ee
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # This tells it to save silently and NOT open a window!
import matplotlib.pyplot as plt
import seaborn as sns
import datetime
# 1. Initialize Google Earth Engine
# (It will prompt you to authenticate in your browser if you haven't already)

PROJECT_ID = 'final-year-project-477507'

try:
    ee.Initialize(project=PROJECT_ID)
except Exception as e:
    print("Authentication required...")
    ee.Authenticate()
    ee.Initialize(project=PROJECT_ID)

print("🌍 GEE Initialized. Traveling back in time to fetch Hebbal Lake data...")

# 2. Define Hebbal Lake Geometry (Approximate central area)
hebbal_lake = ee.Geometry.Point([77.586, 13.045]).buffer(300) 

# Date range: Last 1 year to get a good spread of hot and cool months
start_date = '2024-01-01'
end_date = '2026-03-01'

# ==========================================
# 3. FETCH SENTINEL-2 DATA (NDCI - ALGAE)
# ==========================================
def get_ndci(image):
    # NDCI = (RedEdge - Red) / (RedEdge + Red)
    ndci = image.normalizedDifference(['B5', 'B4']).rename('NDCI')
    mean_dict = ndci.reduceRegion(reducer=ee.Reducer.mean(), geometry=hebbal_lake, scale=10)
    return ee.Feature(None, {'date': image.date().format('YYYY-MM-dd'), 'NDCI': mean_dict.get('NDCI')})

s2_collection = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                 .filterBounds(hebbal_lake)
                 .filterDate(start_date, end_date)
                 .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))
                 .map(get_ndci))

s2_data = s2_collection.getInfo()['features']
s2_records = [{'Date': pd.to_datetime(f['properties']['date']), 'NDCI': f['properties']['NDCI']} 
              for f in s2_data if f['properties'].get('NDCI') is not None]
df_ndci = pd.DataFrame(s2_records).sort_values('Date')


# ==========================================
# 4. FETCH LANDSAT-9 DATA (LST - TEMPERATURE)
# ==========================================
def get_lst(image):
    # Convert Thermal Band 10 from Kelvin to Celsius
    thermal = image.select('ST_B10').multiply(0.00341802).add(149.0).subtract(273.15).rename('LST')
    mean_dict = thermal.reduceRegion(reducer=ee.Reducer.mean(), geometry=hebbal_lake, scale=30)
    return ee.Feature(None, {'date': image.date().format('YYYY-MM-dd'), 'LST': mean_dict.get('LST')})

l9_collection = (ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
                 .filterBounds(hebbal_lake)
                 .filterDate(start_date, end_date)
                 .filter(ee.Filter.lt('CLOUD_COVER', 30))
                 .map(get_lst))

l9_data = l9_collection.getInfo()['features']
l9_records = [{'Date': pd.to_datetime(f['properties']['date']), 'LST': f['properties']['LST']} 
              for f in l9_data if f['properties'].get('LST') is not None]
df_lst = pd.DataFrame(l9_records).sort_values('Date')


# ==========================================
# 5. DATA FUSION (Matching Dates)
# ==========================================
print(f"Sentinel-2 found: {len(df_ndci)} images")
print(f"Landsat-9 found: {len(df_lst)} images")

print("🔄 Fusing optical and thermal timelines...")
# Because Sentinel and Landsat don't always fly on the exact same day, 
# we merge the closest dates together (within 5 days of each other).
df_fused = pd.merge_asof(df_ndci, df_lst, on='Date', direction='nearest', tolerance=pd.Timedelta('15D')).dropna()

print(f"✅ Extracted {len(df_fused)} real historical data points!")

# ==========================================
# 6. PLOT THE REAL DATA
# ==========================================
plt.style.use('seaborn-v0_8-whitegrid')
plt.figure(figsize=(7, 5), dpi=300)

# Calculate real Pearson correlation
real_r = df_fused['LST'].corr(df_fused['NDCI'])

sns.regplot(x=df_fused['LST'], y=df_fused['NDCI'], color='#2c3e50', 
            scatter_kws={'s':60, 'edgecolor':'black', 'alpha':0.8}, 
            line_kws={'color':'#e74c3c', 'linewidth':2, 'linestyle':'--'})

plt.title('REAL DATA: Land Surface Temp vs. NDCI (Hebbal Lake)', pad=15, fontweight='bold')
plt.xlabel('Real Land Surface Temperature (°C)', fontweight='bold')
plt.ylabel('Real Chlorophyll Index (NDCI)', fontweight='bold')

plt.text(df_fused['LST'].min(), df_fused['NDCI'].max(), f'Real Pearson r = {real_r:.2f}\nn = {len(df_fused)} real acquisitions', 
         fontsize=11, bbox=dict(facecolor='white', edgecolor='black', boxstyle='round,pad=0.5'))

plt.tight_layout()
plt.savefig('Fig4_REAL_Correlation.png')
print("✅ Saved Fig4_REAL_Correlation.png to your folder!")