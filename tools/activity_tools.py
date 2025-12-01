# tools/activity_tools.py

import os
import requests
from dotenv import load_dotenv

load_dotenv()
OPENTRIPMAP_API_KEY = os.getenv("OPENTRIPMAP_API_KEY")
GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY")


def geocode_city(city: str) -> dict:
    """
    Use Nominatim or Geoapify to geocode a city name -> lat/lon bounding box or center coordinate.
    For simplicity, use Geoapify forward geocode.
    """
    if not GEOAPIFY_API_KEY:
        return {"status": "error", "error_message": "Missing Geoapify API key"}

    params = {"text": city, "apiKey": GEOAPIFY_API_KEY, "format": "json"}
    url = "https://api.geoapify.com/v1/geocode/search"
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if not results:
            return {
                "status": "error",
                "error_message": f"No geocoding result for city: {city}",
            }
        first = results[0]
        return {
            "status": "success",
            "lat": first.get("lat"),
            "lon": first.get("lon"),
            "bbox": first.get("bbox"),  # may include bounding box
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def search_activities(
    city: str, kinds: str = None, radius_m: int = 5000, limit: int = 10
) -> dict:
    """
    Search for activities / POIs around a city using OpenTripMap API.
    kinds: a comma-separated string of kinds, e.g. 'cultural,historic' or None for any
    Returns: {"status":"success", "activities":[ ... ]} or {"status":"error", ...}
    Each activity: { name, lat, lon, kinds, rate, dist (if available), xid, info_url (if available) }
    """
    if not OPENTRIPMAP_API_KEY:
        return {"status": "error", "error_message": "Missing OpenTripMap API key"}

    # First geocode city to get lat/lon
    geo = geocode_city(city)
    if geo.get("status") != "success":
        return {
            "status": "error",
            "error_message": "Failed to geocode city: " + geo.get("error_message", ""),
        }

    lat = geo["lat"]
    lon = geo["lon"]

    params = {
        "apikey": OPENTRIPMAP_API_KEY,
        "radius": radius_m,
        "limit": limit,
        "lon": lon,
        "lat": lat,
        "format": "json",
    }
    if kinds:
        params["kinds"] = kinds

    url = "https://api.opentripmap.com/0.1/en/places/radius"
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        activities = []
        for item in data:
            activities.append(
                {
                    "name": item.get("name"),
                    "lat": item.get("point", {}).get("lat"),
                    "lon": item.get("point", {}).get("lon"),
                    "kinds": item.get("kinds"),
                    "rate": item.get("rate"),
                    "xid": item.get("xid"),
                    "raw": item,
                }
            )
        return {"status": "success", "activities": activities}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}
