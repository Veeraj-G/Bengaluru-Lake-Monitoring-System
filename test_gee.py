import ee

# 1. Initialize the library with your Project ID
try:
    # I added your specific project ID here:
    ee.Initialize(project='final-year-project-477507') 
    print("Connection Successful!")
except Exception as e:
    print("Connection Failed.")
    print(e)
    exit()

# 2. Run a simple GEE command
print("Asking Google to add 1 + 1...")
result = ee.Number(1).add(1).getInfo()

print(f"Google says the answer is: {result}")

if result == 2:
    print("✅ System is ready for automated satellite access.")