# tools/map_tools.py

import os
import requests
from dotenv import load_dotenv

load_dotenv()
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"


def geocode_place(place_name: str, city: str) -> dict:
    """
    Geocode a specific place name within a city using Google Geocoding API.

    Args:
        place_name: The name of the place e.g. "Senso-ji Temple"
        city:       The city context e.g. "Tokyo"

    Returns:
        {
            "status": "success",
            "name": str,
            "lat": float,
            "lon": float,
            "formatted_address": str
        }
        or {"status": "error", "error_message": str}
    """
    if not GOOGLE_PLACES_API_KEY:
        return {"status": "error", "error_message": "Missing Google Places API key"}

    # Include city in query for better accuracy
    query = f"{place_name}, {city}"

    params = {
        "address": query,
        "key": GOOGLE_PLACES_API_KEY,
    }

    try:
        resp = requests.get(GEOCODING_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "OK" or not data.get("results"):
            return {
                "status": "error",
                "error_message": f"Could not geocode: {query} — {data.get('status')}",
            }

        result = data["results"][0]
        location = result["geometry"]["location"]

        return {
            "status": "success",
            "name": place_name,
            "lat": location["lat"],
            "lon": location["lng"],
            "formatted_address": result.get("formatted_address", ""),
        }

    except Exception as e:
        return {"status": "error", "error_message": str(e)}