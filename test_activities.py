# test_activities.py
from tools.activity_tools import search_activities

result = search_activities("Tokyo")
print("Status:", result["status"])
if result["status"] == "success":
    print("Activities found:", len(result["activities"]))
    print("City coords:", result["city_coords"])
    for a in result["activities"][:3]:
        print(f"  - {a['name']} | rating: {a.get('rating')} | types: {a.get('types', [])[:2]}")
else:
    print("Error:", result["error_message"])