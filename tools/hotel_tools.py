# tools/hotel_tools.py

import os
import requests
from dotenv import load_dotenv

load_dotenv()
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"
PLACES_URL = "https://places.googleapis.com/v1/places:searchNearby"


def geocode_city(city: str) -> dict:
    """
    Use Google Geocoding API to convert a city name to lat/lon.
    Returns: {"status": "success", "lat": ..., "lon": ...}
          or {"status": "error", "error_message": ...}
    """
    if not GOOGLE_PLACES_API_KEY:
        return {"status": "error", "error_message": "Missing Google Places API key"}

    params = {"address": city, "key": GOOGLE_PLACES_API_KEY}

    try:
        resp = requests.get(GEOCODING_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "OK" or not data.get("results"):
            return {
                "status": "error",
                "error_message": f"Could not geocode city: {city} — {data.get('status')}",
            }

        location = data["results"][0]["geometry"]["location"]
        return {
            "status": "success",
            "lat": location["lat"],
            "lon": location["lng"],
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def search_hotels(
    city: str,
    radius_m: int = 10000,
    limit: int = 10,
) -> dict:
    """
    Search for hotels / accommodation in a city using Google Places API (New).

    Args:
        city:      City name to search in.
        radius_m:  Search radius in metres. Default 10,000m (10km).
        limit:     Max results to return. Default 10 (Google max is 20).

    Returns:
        {"status": "success", "hotels": [...]}
        or {"status": "error", "error_message": str}

    Each hotel dict contains:
        name, lat, lon, rating, user_rating_count, address, google_maps_url
    """
    if not GOOGLE_PLACES_API_KEY:
        return {"status": "error", "error_message": "Missing Google Places API key"}

    # Step 1 — geocode city
    geo = geocode_city(city)
    if geo.get("status") != "success":
        return {
            "status": "error",
            "error_message": "Failed to geocode city: " + geo.get("error_message", ""),
        }

    lat = geo["lat"]
    lon = geo["lon"]

    # Step 2 — call Google Places (New) Nearby Search for hotels
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.location,places.types,places.rating,places.userRatingCount,places.formattedAddress,places.googleMapsUri,places.priceLevel",
    }

    body = {
        "includedTypes": ["hotel", "lodging", "motel", "bed_and_breakfast", "resort_hotel"],
        "maxResultCount": min(limit, 20),
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lon},
                "radius": float(radius_m),
            }
        },
        "rankPreference": "POPULARITY",
    }

    try:
        resp = requests.post(PLACES_URL, headers=headers, json=body, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        places = data.get("places", [])

        if not places:
            return {
                "status": "error",
                "error_message": f"No hotels found for {city}. Try increasing radius_m.",
            }

        # Map Google price levels to human-readable labels
        price_map = {
            "PRICE_LEVEL_FREE": "Free",
            "PRICE_LEVEL_INEXPENSIVE": "Budget ($)",
            "PRICE_LEVEL_MODERATE": "Mid-range ($$)",
            "PRICE_LEVEL_EXPENSIVE": "Upscale ($$$)",
            "PRICE_LEVEL_VERY_EXPENSIVE": "Luxury ($$$$)",
        }

        hotels = []
        for place in places:
            name = place.get("displayName", {}).get("text", "").strip()
            if not name:
                continue

            location = place.get("location", {})
            price_level = place.get("priceLevel", "")

            hotels.append({
                "name": name,
                "lat": location.get("latitude"),
                "lon": location.get("longitude"),
                "rating": place.get("rating"),
                "user_rating_count": place.get("userRatingCount"),
                "address": place.get("formattedAddress", "Address unavailable"),
                "price_level": price_map.get(price_level, "Price unavailable"),
                "google_maps_url": place.get("googleMapsUri", ""),
            })

        return {
            "status": "success",
            "hotels": hotels,
            "city_coords": {"lat": lat, "lon": lon},
        }

    except Exception as e:
        return {"status": "error", "error_message": str(e)}