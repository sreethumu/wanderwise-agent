# tools/budget_tools.py

# ---------------------------------------------------------------------------
# Budget estimation tool for WanderWise travel agent.
# Uses tiered cost estimates per city/region rather than a live pricing API.
# Data is based on widely-published travel cost averages (2025-2026).
# ---------------------------------------------------------------------------

# Hotel nightly cost ranges (USD) by Google Places price level
HOTEL_PRICE_RANGES = {
    "PRICE_LEVEL_INEXPENSIVE": (40, 80),
    "PRICE_LEVEL_MODERATE": (100, 200),
    "PRICE_LEVEL_EXPENSIVE": (200, 400),
    "PRICE_LEVEL_VERY_EXPENSIVE": (400, 800),
    "PRICE_LEVEL_FREE": (30, 60),
    "Price unavailable": (100, 200),
}

# Activity cost estimates (USD per person) by category keyword
ACTIVITY_COST_ESTIMATES = {
    "museum": (10, 25),
    "art_gallery": (10, 20),
    "historical_place": (5, 20),
    "amusement_park": (30, 80),
    "zoo": (15, 35),
    "aquarium": (15, 30),
    "theme_park": (50, 120),
    "national_park": (5, 35),
    "park": (0, 5),
    "tourist_attraction": (10, 30),
    "landmark": (0, 15),
    "night_club": (20, 60),
    "bar": (15, 40),
    "restaurant": (20, 60),
    "default": (10, 25),
}

# Daily food budget estimates (USD per person) by budget tier
FOOD_DAILY_BUDGET = {
    "budget": (20, 40),
    "mid-range": (50, 100),
    "luxury": (120, 250),
}

# Daily transport estimates (USD per person) by city
TRANSPORT_DAILY_BUDGET = {
    "tokyo": (10, 20),
    "osaka": (8, 18),
    "kyoto": (8, 15),
    "new york": (15, 30),
    "london": (15, 25),
    "paris": (12, 22),
    "sydney": (12, 20),
    "singapore": (8, 15),
    "bangkok": (5, 15),
    "bali": (5, 20),
    "rome": (8, 15),
    "barcelona": (8, 15),
    "dubai": (10, 25),
    "default": (10, 20),
}


def _get_transport_estimate(city: str) -> tuple:
    return TRANSPORT_DAILY_BUDGET.get(city.lower().strip(), TRANSPORT_DAILY_BUDGET["default"])


def _get_activity_cost_by_keyword(keyword: str) -> tuple:
    keyword = keyword.lower().strip()
    for key in ACTIVITY_COST_ESTIMATES:
        if key in keyword or keyword in key:
            return ACTIVITY_COST_ESTIMATES[key]
    return ACTIVITY_COST_ESTIMATES["default"]


def estimate_budget(
    city: str,
    num_days: int,
    num_people: int,
    budget_tier: str,
    hotel_price_level: str,
    activity_names: str = "",
    activity_types: str = "",
    activities_per_day: int = 2,
) -> dict:
    """
    Estimate total trip budget based on hotel tier, activities, food, and transport.

    Args:
        city:               Destination city name.
        num_days:           Number of days for the trip.
        num_people:         Number of travelers.
        budget_tier:        One of 'budget', 'mid-range', or 'luxury'.
        hotel_price_level:  Google Places price level e.g. 'PRICE_LEVEL_EXPENSIVE'.
        activity_names:     Comma-separated activity names e.g. 'Senso-ji Temple, Ueno Zoo'.
        activity_types:     Comma-separated activity type keywords e.g. 'museum,park,tourist_attraction'.
        activities_per_day: How many activities per day to budget for (default 2).

    Returns:
        {
            "status": "success",
            "summary": { ... },
            "breakdown": { ... },
            "note": str
        }
    """
    tier = budget_tier.lower().strip()
    if tier not in FOOD_DAILY_BUDGET:
        tier = "mid-range"

    # --- Hotel cost ---
    hotel_range = HOTEL_PRICE_RANGES.get(hotel_price_level, HOTEL_PRICE_RANGES["Price unavailable"])
    hotel_low = hotel_range[0] * num_days
    hotel_high = hotel_range[1] * num_days

    # --- Food cost ---
    food_range = FOOD_DAILY_BUDGET[tier]
    food_low = food_range[0] * num_days * num_people
    food_high = food_range[1] * num_days * num_people

    # --- Transport cost ---
    transport_range = _get_transport_estimate(city)
    transport_low = transport_range[0] * num_days * num_people
    transport_high = transport_range[1] * num_days * num_people

    # --- Activities cost ---
    # Parse activity types from comma-separated string
    type_list = [t.strip() for t in activity_types.split(",") if t.strip()] if activity_types else []
    name_list = [n.strip() for n in activity_names.split(",") if n.strip()] if activity_names else []

    total_activities = num_days * activities_per_day
    activity_costs_low = 0
    activity_costs_high = 0
    activity_breakdown = []

    for i in range(total_activities):
        # Use type if available, otherwise fall back to default
        keyword = type_list[i] if i < len(type_list) else "default"
        low, high = _get_activity_cost_by_keyword(keyword)
        cost_low = low * num_people
        cost_high = high * num_people
        activity_costs_low += cost_low
        activity_costs_high += cost_high

        name = name_list[i] if i < len(name_list) else f"Activity {i+1}"
        activity_breakdown.append({
            "name": name,
            "estimated_cost": f"${cost_low}–${cost_high} total",
        })

    # --- Totals ---
    total_low = hotel_low + food_low + transport_low + activity_costs_low
    total_high = hotel_high + food_high + transport_high + activity_costs_high

    return {
        "status": "success",
        "summary": {
            "destination": city,
            "duration": f"{num_days} days",
            "travelers": num_people,
            "budget_tier": budget_tier,
            "estimated_total": f"${total_low:,}–${total_high:,} USD",
            "estimated_per_person": f"${total_low // num_people:,}–${total_high // num_people:,} USD",
        },
        "breakdown": {
            "hotel": f"${hotel_low:,}–${hotel_high:,} USD ({num_days} nights)",
            "food": f"${food_low:,}–${food_high:,} USD ({num_days} days × {num_people} {'person' if num_people == 1 else 'people'})",
            "transport": f"${transport_low:,}–${transport_high:,} USD ({num_days} days × {num_people} {'person' if num_people == 1 else 'people'})",
            "activities": f"${activity_costs_low:,}–${activity_costs_high:,} USD ({total_activities} activities)",
            "activity_details": activity_breakdown,
        },
        "note": "All estimates are approximate and based on typical travel costs. Actual costs may vary.",
    }