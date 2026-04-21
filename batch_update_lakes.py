import requests

lakes = ["hebbal", "bellandur", "ulsoor", "varthur", "madiwala", "jakkur", "sankey", "agara", "yelahanka", "nagavara"]

print("--- INITIALIZING CITY-WIDE SATELLITE UPLINK ---")
for lake in lakes:
    print(f"Triggering update for: {lake.upper()}")
    response = requests.get(f"http://127.0.0.1:8000/update-satellite-data/{lake}")
    print(response.json())