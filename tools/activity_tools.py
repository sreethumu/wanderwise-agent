# tools/activity_tools.py

import os
import requests
from dotenv import load_dotenv

load_dotenv()
OPENTRIPMAP_API_KEY = os.getenv("OPENTRIPMAP_API_KEY")
GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY")

# Default kinds for tourist-friendly results
DEFAULT_KINDS = "interesting_places,cultural,historic,natural,architecture,museums,religion,amusements"


def geocode_city(city: str) -> dict:
    """
    Use Geoapify to geocode a city name -> lat/lon.
    Returns: {"status": "success", "lat": ..., "lon": ..., "bbox": ...}
          or {"status": "error", "error_message": ...}
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
            "bbox": first.get("bbox"),
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def search_activities(
    city: str,
    kinds: str = DEFAULT_KINDS,
    radius_m: int = 10000,
    limit: int = 20,
    min_rate: int = 2,
) -> dict:
    """
    Search for activities / POIs around a city using OpenTripMap API.

    Args:
        city:      City name to search around.
        kinds:     Comma-separated OpenTripMap kinds. Defaults to popular tourist categories.
        radius_m:  Search radius in metres. Default 10,000m (10km).
        limit:     Max number of results to return (after filtering). Default 20.
        min_rate:  Minimum OpenTripMap 'rate' score (0–7) to include. Default 2.

    Returns:
        {"status": "success", "activities": [...], "total_raw": int, "city_coords": {...}}
        or {"status": "error", "error_message": str}

    Each activity dict contains:
        name, lat, lon, kinds, rate (int), xid
    """
    if not OPENTRIPMAP_API_KEY:
        return {"status": "error", "error_message": "Missing OpenTripMap API key"}

    # Step 1 — geocode the city
    geo = geocode_city(city)
    if geo.get("status") != "success":
        return {
            "status": "error",
            "error_message": "Failed to geocode city: " + geo.get("error_message", ""),
        }

    lat = geo["lat"]
    lon = geo["lon"]

    # Step 2 — fetch POIs from OpenTripMap
    params = {
        "apikey": OPENTRIPMAP_API_KEY,
        "radius": radius_m,
        "limit": 100,           # fetch more up front so filtering doesn't starve results
        "lon": lon,
        "lat": lat,
        "kinds": kinds,
        "format": "json",
    }

    url = "https://api.opentripmap.com/0.1/en/places/radius"

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if not isinstance(data, list):
            return {
                "status": "error",
                "error_message": f"Unexpected API response format: {type(data).__name__}",
            }

        total_raw = len(data)
        activities = []

        for item in data:
            # Skip places with no name or blank name
            name = item.get("name", "").strip()
            if not name:
                continue

            # rate comes back as a string from the API — cast safely
            rate = int(item.get("rate") or 0)
            if rate < min_rate:
                continue

            activities.append(
                {
                    "name": name,
                    "lat": item.get("point", {}).get("lat"),
                    "lon": item.get("point", {}).get("lon"),
                    "kinds": item.get("kinds"),
                    "rate": rate,
                    "xid": item.get("xid"),
                }
            )

            # Stop once we have enough
            if len(activities) >= limit:
                break

        return {
            "status": "success",
            "activities": activities,
            "total_raw": total_raw,          # useful for debugging
            "city_coords": {"lat": lat, "lon": lon},
        }

    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def get_activity_details(xid: str) -> dict:
    """
    Fetch detailed info for a single POI by its OpenTripMap xid.
    Useful for getting descriptions, Wikipedia links, images, etc.

    Returns: {"status": "success", "details": {...}} or {"status": "error", ...}
    """
    if not OPENTRIPMAP_API_KEY:
        return {"status": "error", "error_message": "Missing OpenTripMap API key"}

    url = f"https://api.opentripmap.com/0.1/en/places/xid/{xid}"
    params = {"apikey": OPENTRIPMAP_API_KEY}

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return {"status": "success", "details": data}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}