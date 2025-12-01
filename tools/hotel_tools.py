# tools/hotel_tools.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()
GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY")


def geocode_city(city: str) -> dict:
    """Use Geoapify Geocoding API to get coordinates (lat, lon) of a city."""
    if not GEOAPIFY_API_KEY:
        return {"status": "error", "error_message": "Missing Geoapify API key."}
    url = "https://api.geoapify.com/v1/geocode/search"
    params = {
        "text": city,
        "limit": 1,
        "apiKey": GEOAPIFY_API_KEY,
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    features = data.get("features", [])
    if not features:
        return {"status": "error", "error_message": f"Could not geocode city: {city}"}
    coords = features[0]["geometry"]["coordinates"]  # [lon, lat]
    return {"status": "success", "lon": coords[0], "lat": coords[1]}


def search_hotels(city: str, radius_m: int = 5000, limit: int = 10) -> dict:
    """
    Search for hotel / accommodation options in the given city using Geoapify Places API.
    Returns: {"status": "success", "hotels": [ ... ]} or {"status":"error", "error_message": "..."}
    Each hotel entry: { name, address, lon, lat, rating (if available), raw_properties }
    """
    if not GEOAPIFY_API_KEY:
        return {"status": "error", "error_message": "Missing Geoapify API key."}

    # 1. Geocode city name
    geo = geocode_city(city)
    if geo.get("status") != "success":
        return {"status": "error", "error_message": geo.get("error_message")}
    lon = geo["lon"]
    lat = geo["lat"]

    url = "https://api.geoapify.com/v2/places"
    params = {
        "apiKey": GEOAPIFY_API_KEY,
        "categories": "accommodation.hotel,accommodation.hostel,accommodation.apartment",
        # search within a circle around city center
        "filter": f"circle:{lon},{lat},{radius_m}",
        "limit": limit,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        features = data.get("features", [])
        hotels = []
        for feat in features:
            prop = feat.get("properties", {})
            hotels.append(
                {
                    "name": prop.get("name", "Unnamed hotel"),
                    "address": prop.get("formatted", "Address not available"),
                    "lat": feat.get("geometry", {}).get("coordinates", [None, None])[1],
                    "lon": feat.get("geometry", {}).get("coordinates", [None, None])[0],
                    "price": prop.get("rate"),  # may be None
                    "rating": prop.get("rating"),  # may be None
                    "raw": prop,
                }
            )
        return {"status": "success", "hotels": hotels}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}
