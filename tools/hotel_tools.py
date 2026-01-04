# tools/hotel_tools.py
import os
import logging
import requests
from dotenv import load_dotenv

load_dotenv()
GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY")

logger = logging.getLogger(__name__)


def geocode_city(city: str) -> dict:
    """Use Geoapify Geocoding API to get coordinates (lat, lon) of a city."""
    logger.info(f"🔍 Geocoding city: {city}")
    if not GEOAPIFY_API_KEY:
        logger.error("Missing Geoapify API key")
        return {"status": "error", "error_message": "Missing Geoapify API key."}
    url = "https://api.geoapify.com/v1/geocode/search"
    params = {
        "text": city,
        "limit": 1,
        "apiKey": GEOAPIFY_API_KEY,
    }
    logger.debug(f"   API Call: GET {url}")
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    features = data.get("features", [])
    if not features:
        logger.warning(f"   No geocoding results found for: {city}")
        return {"status": "error", "error_message": f"Could not geocode city: {city}"}
    coords = features[0]["geometry"]["coordinates"]  # [lon, lat]
    result = {"status": "success", "lon": coords[0], "lat": coords[1]}
    logger.info(f"   ✓ Geocoded {city} → lat={result['lat']}, lon={result['lon']}")
    return result


def search_hotels(city: str, radius_m: int = 5000, limit: int = 10) -> dict:
    """
    Search for hotel / accommodation options in the given city using Geoapify Places API.
    Returns: {"status": "success", "hotels": [ ... ]} or {"status":"error", "error_message": "..."}
    Each hotel entry: { name, address, lon, lat, rating (if available), raw_properties }
    """
    logger.info(
        f"🏨 Tool: search_hotels(city={city}, radius_m={radius_m}, limit={limit})"
    )
    if not GEOAPIFY_API_KEY:
        logger.error("Missing Geoapify API key")
        return {"status": "error", "error_message": "Missing Geoapify API key."}

    # 1. Geocode city name
    geo = geocode_city(city)
    if geo.get("status") != "success":
        logger.error(f"   Failed to geocode {city}")
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
        logger.debug(
            f"   API Call: GET {url} | categories: accommodation | radius: {radius_m}m"
        )
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        features = data.get("features", [])
        logger.info(f"   ✓ Found {len(features)} hotels")
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
        logger.error(f"   API Error: {str(e)}")
        return {"status": "error", "error_message": str(e)}
