# tools/activity_tools.py

import os
import requests
from dotenv import load_dotenv

load_dotenv()
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"
PLACES_URL = "https://places.googleapis.com/v1/places:searchNearby"

# Mapping of interest keywords to Google Places (New) includedTypes
KINDS_TO_GOOGLE_TYPES = {
    "cultural": ["museum", "art_gallery", "cultural_center"],
    "historic": ["historical_place", "monument", "ruins"],
    "natural": ["national_park", "park", "botanical_garden", "hiking_area"],
    "architecture": ["landmark", "historical_place"],
    "museums": ["museum", "art_gallery"],
    "religion": ["church", "hindu_temple", "mosque", "synagogue", "buddhist_temple"],
    "amusements": ["amusement_park", "zoo", "aquarium", "theme_park"],
    "food": ["restaurant", "food", "bakery", "cafe"],
    "shopping": ["shopping_mall", "market", "store"],
    "nightlife": ["bar", "night_club"],
    "outdoors": ["park", "national_park", "hiking_area", "beach"],
    "beaches": ["beach"],
}

DEFAULT_TYPES = [
    "tourist_attraction",
    "museum",
    "art_gallery",
    "historical_place",
    "park",
    "zoo",
    "aquarium",
    "amusement_park",
    "beach",
]


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


def parse_kinds_to_google_types(kinds: str) -> list:
    """
    Convert a comma-separated kinds string (e.g. 'cultural,museums,food')
    into a list of Google Places includedTypes.
    Falls back to DEFAULT_TYPES if no match found.
    """
    if not kinds:
        return DEFAULT_TYPES

    google_types = []
    for kind in kinds.split(","):
        kind = kind.strip().lower()
        mapped = KINDS_TO_GOOGLE_TYPES.get(kind)
        if mapped:
            google_types.extend(mapped)

    # Deduplicate while preserving order
    seen = set()
    unique_types = []
    for t in google_types:
        if t not in seen:
            seen.add(t)
            unique_types.append(t)

    return unique_types if unique_types else DEFAULT_TYPES


def search_activities(
    city: str,
    kinds: str = None,
    radius_m: int = 10000,
    limit: int = 20,
) -> dict:
    """
    Search for activities / POIs around a city using Google Places API (New).

    Args:
        city:      City name to search around.
        kinds:     Comma-separated interest types e.g. 'cultural,museums,food'.
                   Maps to Google Places includedTypes automatically.
        radius_m:  Search radius in metres. Default 10,000m (10km).
        limit:     Max results to return. Default 20 (Google max is 20).

    Returns:
        {"status": "success", "activities": [...], "city_coords": {...}}
        or {"status": "error", "error_message": str}

    Each activity dict contains:
        name, lat, lon, types, rating, user_rating_count, address, google_maps_url
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

    # Step 2 — map kinds to Google Place types
    included_types = parse_kinds_to_google_types(kinds)

    # Step 3 — call Google Places (New) Nearby Search
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.location,places.types,places.rating,places.userRatingCount,places.formattedAddress,places.googleMapsUri",
    }

    body = {
        "includedTypes": included_types[:50],  # Google allows max 50 types
        "maxResultCount": min(limit, 20),       # Google max is 20
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
                "error_message": f"No activities found for {city}. Try increasing radius_m or broadening interests.",
            }

        activities = []
        for place in places:
            name = place.get("displayName", {}).get("text", "").strip()
            if not name:
                continue

            location = place.get("location", {})
            activities.append({
                "name": name,
                "lat": location.get("latitude"),
                "lon": location.get("longitude"),
                "types": place.get("types", []),
                "rating": place.get("rating"),
                "user_rating_count": place.get("userRatingCount"),
                "address": place.get("formattedAddress", "Address unavailable"),
                "google_maps_url": place.get("googleMapsUri", ""),
            })

        return {
            "status": "success",
            "activities": activities,
            "city_coords": {"lat": lat, "lon": lon},
        }

    except Exception as e:
        return {"status": "error", "error_message": str(e)}