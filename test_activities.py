# test_activities.py  (put this in your project root)
from tools.activity_tools import search_activities

result = search_activities("Tokyo")
print("Status:", result["status"])
if result["status"] == "success":
    print("Total raw POIs from API:", result["total_raw"])
    print("Filtered activities:", len(result["activities"]))
    for a in result["activities"][:3]:
        print(" -", a["name"], "| rate:", a["rate"])
else:
    print("Error:", result["error_message"])