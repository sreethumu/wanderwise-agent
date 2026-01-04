# tools/activity_tools.py

import os
import logging
import requests
from dotenv import load_dotenv

load_dotenv()
OPENTRIPMAP_API_KEY = os.getenv("OPENTRIPMAP_API_KEY")
GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY")

logger = logging.getLogger(__name__)


def geocode_city(city: str) -> dict:
    """
    Use Nominatim or Geoapify to geocode a city name -> lat/lon bounding box or center coordinate.
    For simplicity, use Geoapify forward geocode.
    """
    logger.debug(f"🔍 Geocoding city: {city}")
    if not GEOAPIFY_API_KEY:
        logger.error("Missing Geoapify API key")
        return {"status": "error", "error_message": "Missing Geoapify API key"}

    params = {"text": city, "apiKey": GEOAPIFY_API_KEY, "format": "json"}
    url = "https://api.geoapify.com/v1/geocode/search"
    try:
        logger.debug(f"   API Call: GET {url}")
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if not results:
            logger.warning(f"   No geocoding results found for: {city}")
            return {
                "status": "error",
                "error_message": f"No geocoding result for city: {city}",
            }
        first = results[0]
        result = {
            "status": "success",
            "lat": first.get("lat"),
            "lon": first.get("lon"),
            "bbox": first.get("bbox"),  # may include bounding box
        }
        logger.debug(f"   ✓ Geocoded {city} → lat={result['lat']}, lon={result['lon']}")
        return result
    except Exception as e:
        logger.error(f"   API Error: {str(e)}")
        return {"status": "error", "error_message": str(e)}


def search_activities(
    city: str, kinds: str | None = None, radius_m: int = 5000, limit: int = 10
) -> dict:
    """
    Search for activities / POIs around a city using OpenTripMap API.
    kinds: a comma-separated string of kinds, e.g. 'cultural,historic' or None for any
    Returns: {"status":"success", "activities":[ ... ]} or {"status":"error", ...}
    Each activity: { name, lat, lon, kinds, rate, dist (if available), xid, info_url (if available) }
    """
    logger.info(
        f"🎭 Tool: search_activities(city={city}, kinds={kinds}, radius_m={radius_m}, limit={limit})"
    )
    if not OPENTRIPMAP_API_KEY:
        logger.error("Missing OpenTripMap API key")
        return {"status": "error", "error_message": "Missing OpenTripMap API key"}

    # First geocode city to get lat/lon
    geo = geocode_city(city)
    if geo.get("status") != "success":
        logger.error(f"   Failed to geocode {city}")
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
        logger.debug(f"   API Call: GET {url} | radius: {radius_m}m, limit: {limit}")
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"   ✓ Found {len(data)} activities")
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
        logger.error(f"   API Error: {str(e)}")
        return {"status": "error", "error_message": str(e)}
