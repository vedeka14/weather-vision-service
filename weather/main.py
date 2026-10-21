from datetime import date, timedelta

import httpx
from fastapi import FastAPI, HTTPException, Query

app = FastAPI(title="Weather service")

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
MAX_DAYS_AHEAD = 16  # Open-Meteo only forecasts this far ahead


@app.get("/health")
def health():
    return {"ok": True}


def call_open_meteo(url, params):
    """Call Open-Meteo and turn any problem into a clear error message."""
    try:
        r = httpx.get(url, params=params, timeout=10)
    except httpx.HTTPError:
        raise HTTPException(503, "Weather website is not reachable right now. Try again later.")
    if r.status_code != 200:
        try:
            reason = r.json().get("reason", "unknown problem")
        except ValueError:
            reason = "unknown problem"
        raise HTTPException(502, f"Weather website refused the request: {reason}")
    return r.json()


def find_city(name):
    """Turn a city name like 'Goa' into coordinates."""
    data = call_open_meteo(GEOCODE_URL, {"name": name, "count": 1})
    if not data.get("results"):
        raise HTTPException(404, f"Could not find a place called '{name}'.")
    place = data["results"][0]
    return place["latitude"], place["longitude"], f"{place['name']}, {place.get('country', '')}".strip(", ")


def temperature_label(high):
    if high >= 32:
        return "hot"
    if high < 20:
        return "cold"
    return "mild"


# Shared words for clothing. The vision service should tag uploaded clothes
# with these same words, so the gap agent can match weather needs to the wardrobe.
TYPES = ["t-shirt", "shirt", "top", "kurta", "dress", "skirt", "shorts", "jeans",
         "trousers", "sweater", "hoodie", "jacket", "coat", "sandals", "sneakers", "shoes", "boots"]
MATERIALS = ["cotton", "linen", "rayon", "polyester", "denim", "wool", "fleece",
             "leather", "suede", "silk", "nylon"]
WARMTH = ["light", "medium", "warm", "very_warm"]


def clothing_needs(high, low, rainy):
    """Rule-based description of what the day's weather needs from an outfit.

    It never names a specific garment from the wardrobe; the gap agent matches
    these needs against the user's uploaded clothes.
    """
    label = temperature_label(high)
    if label == "hot":
        needs = {
            "warmth": "light",
            "sleeves": "short",
            "types_prefer": ["t-shirt", "shirt", "top", "kurta", "dress", "skirt", "shorts", "sandals"],
            "types_avoid": ["sweater", "hoodie", "jacket", "coat", "boots"],
            "materials_prefer": ["cotton", "linen", "rayon"],
            "materials_avoid": ["wool", "fleece", "leather", "denim"],
            "colors_prefer": ["light"],
            "layer_for_evening": False,
            "accessories": ["sunglasses", "cap or hat", "sunscreen"],
        }
    elif label == "mild":
        needs = {
            "warmth": "medium",
            "sleeves": "any",
            "types_prefer": ["t-shirt", "shirt", "top", "kurta", "dress", "jeans", "trousers", "sneakers"],
            "types_avoid": ["coat"],
            "materials_prefer": ["cotton", "linen", "denim", "rayon"],
            "materials_avoid": ["fleece"],
            "colors_prefer": [],
            "layer_for_evening": low < 18,
            "accessories": [],
        }
    else:
        very_cold = high < 10
        needs = {
            "warmth": "very_warm" if very_cold else "warm",
            "sleeves": "long",
            "types_prefer": ["sweater", "hoodie", "jacket", "jeans", "trousers", "shoes", "boots"]
                            + (["coat"] if very_cold else []),
            "types_avoid": ["shorts", "sandals", "skirt"],
            "materials_prefer": ["wool", "fleece", "denim"],
            "materials_avoid": ["linen"],
            "colors_prefer": [],
            "layer_for_evening": True,
            "accessories": ["scarf", "gloves"] if very_cold else [],
        }

    needs["waterproof"] = rainy
    if rainy:
        needs["materials_prefer"] = [m for m in needs["materials_prefer"] if m != "denim"] + ["polyester", "nylon"]
        needs["materials_avoid"] = needs["materials_avoid"] + ["suede", "silk"]
        needs["colors_avoid"] = ["white"]
        needs["accessories"] = needs["accessories"] + ["umbrella or raincoat"]
    else:
        needs["colors_avoid"] = []
    return needs


def trip_summary(days):
    """Roll the daily needs up into one view of the whole trip, for packing."""
    needs = [d["needs"] for d in days]
    return {
        "warmth_levels": [w for w in WARMTH if any(n["warmth"] == w for n in needs)],
        "rainy_days": sum(d["rainy"] for d in days),
        "needs_evening_layer": any(n["layer_for_evening"] for n in needs),
        "needs_waterproof": any(n["waterproof"] for n in needs),
        "accessories": sorted({a for n in needs for a in n["accessories"]}),
    }


@app.get("/weather/vocabulary")
def vocabulary():
    """The clothing words this service uses, for the vision service to share."""
    return {"types": TYPES, "materials": MATERIALS, "warmth": WARMTH}


@app.get("/weather")
def weather(
    city: str | None = Query(None, description="City name, e.g. Goa. Used instead of lat/lon."),
    lat: float = 15.2993,
    lon: float = 74.124,
    days: int = Query(4, ge=1, le=MAX_DAYS_AHEAD),
    start_date: date | None = Query(None, description="First day of the trip, e.g. 2026-10-20. Default: today."),
    end_date: date | None = Query(None, description="Last day of the trip. Default: start_date + days - 1."),
):
    place = None
    if city:
        lat, lon, place = find_city(city)

    today = date.today()
    start = start_date or today
    end = end_date or start + timedelta(days=days - 1)
    last_allowed = today + timedelta(days=MAX_DAYS_AHEAD - 1)
    if end < start:
        raise HTTPException(400, "end_date must be on or after start_date.")
    if start < today - timedelta(days=1):
        raise HTTPException(400, "start_date is in the past.")
    if end > last_allowed:
        raise HTTPException(400, f"Forecasts only go {MAX_DAYS_AHEAD} days ahead. Pick dates up to {last_allowed}.")

    data = call_open_meteo(FORECAST_URL, {
        "latitude": lat, "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "timezone": "auto",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
    })
    d = data["daily"]

    result = []
    for i in range(len(d["time"])):
        high = d["temperature_2m_max"][i]
        low = d["temperature_2m_min"][i]
        rain = d["precipitation_probability_max"][i] or 0
        rainy = rain >= 60
        result.append({
            "date": d["time"][i],
            "max": high,
            "min": low,
            "rain_chance": rain,
            "label": temperature_label(high),
            "rainy": rainy,
            "needs": clothing_needs(high, low, rainy),
        })

    return {
        "place": place or f"{lat}, {lon}",
        "timezone": data.get("timezone"),
        "days": result,
        "trip": trip_summary(result),
    }
