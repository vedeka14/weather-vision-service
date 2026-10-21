"""Demo: how the gap agent will use the weather service's `needs`.

Run the weather service first (uvicorn main:app --port 8004), then in a
second terminal:

    python outfit_demo.py Goa              # uses the sample wardrobe below
    python outfit_demo.py Goa --user u1    # uses your real wardrobe-ai service (port 8001)
"""
import sys

import httpx

WEATHER_URL = "http://localhost:8004/weather"
WARDROBE_URL = "http://localhost:8001/wardrobe/items"

# Sample wardrobe, already in the shared vocabulary from /weather/vocabulary.
SAMPLE_WARDROBE = [
    {"name": "white linen shirt", "slot": "top", "type": "shirt", "material": "linen", "color": ["white"], "warmth": "light"},
    {"name": "blue cotton t-shirt", "slot": "top", "type": "t-shirt", "material": "cotton", "color": ["blue"], "warmth": "light"},
    {"name": "grey wool sweater", "slot": "top", "type": "sweater", "material": "wool", "color": ["grey"], "warmth": "warm"},
    {"name": "black denim jeans", "slot": "bottom", "type": "jeans", "material": "denim", "color": ["black"], "warmth": "medium"},
    {"name": "beige cotton shorts", "slot": "bottom", "type": "shorts", "material": "cotton", "color": ["beige"], "warmth": "light"},
    {"name": "brown leather sandals", "slot": "footwear", "type": "sandals", "material": "leather", "color": ["brown"], "warmth": "light"},
    {"name": "white sneakers", "slot": "footwear", "type": "sneakers", "material": "polyester", "color": ["white"], "warmth": "medium"},
]

# wardrobe-ai stores the YOLO category (e.g. "Kurti"). This table translates each
# one into the weather vocabulary: (slot, type, warmth).
# "one-piece" fills top and bottom; "layer" is worn over a top.
CATEGORY_MAP = {
    "T-Shirt": ("top", "t-shirt", "light"),
    "Shirt": ("top", "shirt", "light"),
    "Kurti": ("top", "kurta", "light"),
    "Kameez": ("top", "kurta", "light"),
    "Hoodie": ("layer", "hoodie", "warm"),
    "Jacket": ("layer", "jacket", "warm"),
    "Blazer": ("layer", "jacket", "medium"),
    "Dress": ("one-piece", "dress", "light"),
    "Maxi": ("one-piece", "dress", "light"),
    "Saree": ("one-piece", "dress", "light"),
    "Anarkali": ("one-piece", "dress", "medium"),
    "Lehenga": ("one-piece", "dress", "medium"),
    "Sherwani": ("one-piece", "kurta", "warm"),
    "Jeans": ("bottom", "jeans", "medium"),
    "Skirt": ("bottom", "skirt", "light"),
    "Shalwar": ("bottom", "trousers", "light"),
    "Sharara": ("bottom", "trousers", "light"),
    "Shoes": ("footwear", "shoes", "medium"),
    "Slippers": ("footwear", "sandals", "light"),
    # Accessories aren't matched to weather yet.
    "Dupatta": ("accessory", None, None),
    "Bag": ("accessory", None, None),
    "Jewellery": ("accessory", None, None),
    "Sunglasses": ("accessory", None, None),
}

SLOTS = ["top", "bottom", "footwear"]
LAYERS = ("sweater", "hoodie", "jacket", "coat")
SLOT_TYPES = {
    "top": ["t-shirt", "shirt", "top", "kurta", "dress", "sweater", "hoodie"],
    "bottom": ["shorts", "skirt", "jeans", "trousers"],
    "footwear": ["sandals", "sneakers", "shoes", "boots"],
}


def from_wardrobe_item(item):
    """Turn one wardrobe-ai item into the shape the matching rules use."""
    if not item.get("category") or item["category"] not in CATEGORY_MAP:
        return None  # not tagged yet ("pending"), or a category we don't map
    slot, type_, warmth = CATEGORY_MAP[item["category"]]
    if slot == "accessory":
        return None
    colors = [c.lower() for c in (item.get("color") or [])]
    material = (item.get("material") or "").lower() or None
    label = " ".join(colors[:1] + ([material] if material else []) + [item["category"]])
    return {"name": label, "id": item["id"], "slot": slot, "type": type_,
            "material": material, "color": colors, "warmth": warmth}


def load_wardrobe(user_id):
    r = httpx.get(WARDROBE_URL, params={"user_id": user_id, "limit": 200}, timeout=20)
    r.raise_for_status()
    items = r.json()["items"]
    converted = [from_wardrobe_item(i) for i in items]
    usable = [c for c in converted if c]
    skipped = len(items) - len(usable)
    if skipped:
        print(f"({skipped} item(s) skipped: not tagged yet, or accessories)\n")
    return usable


def buy_suggestion(slot, needs):
    """Describe what to buy for an empty slot, in the shared vocabulary."""
    types = [t for t in needs["types_prefer"] if t in SLOT_TYPES[slot]] or SLOT_TYPES[slot][:2]
    if slot == "footwear":
        extra = "waterproof (floaters, rubber)" if needs["waterproof"] else ""
    else:
        extra = "in " + " or ".join(needs["materials_prefer"][:2])
    return f"{slot}: {' or '.join(types[:2])} {extra}".strip()


def fits(item, needs):
    """Hard rules: drop anything the weather says to avoid."""
    if item["type"] in needs["types_avoid"]:
        return False
    # Fabric rules are for clothes; shoes only follow the rain rule below.
    if item["slot"] != "footwear" and item["material"] in needs["materials_avoid"]:
        return False
    if any(c in needs["colors_avoid"] for c in item["color"]):
        return False
    if needs["waterproof"] and item["slot"] == "footwear" and item["material"] in ("leather", "suede"):
        return False
    return True


def score(item, needs):
    """Soft rules: rank what's left by how well it suits the weather."""
    s = 0
    s += 2 if item["type"] in needs["types_prefer"] else 0
    s += 2 if item["material"] in needs["materials_prefer"] else 0
    s += 1 if item["warmth"] == needs["warmth"] else 0
    return s


def best(wardrobe, slots, needs):
    options = [i for i in wardrobe if i["slot"] in slots and fits(i, needs)]
    return max(options, key=lambda i: score(i, needs)) if options else None


def outfit_for_day(day, wardrobe):
    needs = day["needs"]
    picks, missing = {}, []

    # A dress, saree etc. counts as top and bottom together.
    top = best(wardrobe, ("top", "one-piece"), needs)
    if top:
        picks["top" if top["slot"] == "top" else "outfit"] = top
    else:
        missing.append(buy_suggestion("top", needs))
    if not top or top["slot"] != "one-piece":
        bottom = best(wardrobe, ("bottom",), needs)
        if bottom:
            picks["bottom"] = bottom
        else:
            missing.append(buy_suggestion("bottom", needs))
    shoes = best(wardrobe, ("footwear",), needs)
    if shoes:
        picks["footwear"] = shoes
    else:
        missing.append(buy_suggestion("footwear", needs))

    top_is_layer = top is not None and top["type"] in LAYERS
    if needs["layer_for_evening"] and not top_is_layer:
        layers = [i for i in wardrobe if i["type"] in LAYERS and fits(i, needs)]
        if layers:
            picks["evening layer"] = layers[0]
        else:
            missing.append("evening layer: light jacket or sweater")
    return picks, missing


def main():
    args = sys.argv[1:]
    user = None
    if "--user" in args:
        i = args.index("--user")
        user = args[i + 1]
        args = args[:i] + args[i + 2:]
    city = args[0] if args else "Goa"

    wardrobe = load_wardrobe(user) if user else SAMPLE_WARDROBE
    if not wardrobe:
        print("No tagged clothes found. Upload items with a category first.")
        return

    r = httpx.get(WEATHER_URL, params={"city": city, "days": 4}, timeout=20)
    r.raise_for_status()
    data = r.json()
    print(f"Outfits for {data['place']}\n")
    for day in data["days"]:
        picks, missing = outfit_for_day(day, wardrobe)
        rain = ", rainy" if day["rainy"] else ""
        print(f"{day['date']}  {day['max']}°C {day['label']}{rain}")
        for slot, item in picks.items():
            print(f"   {slot:14} {item['name']}")
        for m in missing:
            print(f"   BUY  {m}")
        if day["needs"]["accessories"]:
            print(f"   carry          {', '.join(day['needs']['accessories'])}")
        print()


if __name__ == "__main__":
    main()
