"""Check that the weather service and a running wardrobe-ai service still fit together.

Run it from the weather folder. Start both services first (wardrobe on 8001, weather on 8004), then run:
    python check_compat.py u1
where u1 is a user_id that has some clothes uploaded.
"""
import sys

import httpx

from outfit_demo import CATEGORY_MAP

WARDROBE = "http://localhost:8001"
WEATHER = "http://localhost:8004"


def check(name, ok, detail=""):
    print(f"[{'OK' if ok else 'PROBLEM'}] {name}{': ' + detail if detail else ''}")
    return ok


def main():
    user = sys.argv[1] if len(sys.argv) > 1 else "u1"
    all_ok = True

    try:
        w = httpx.get(f"{WARDROBE}/health", timeout=5).json()
        all_ok &= check("wardrobe service is running on 8001", True)
        all_ok &= check("wardrobe enrichment setting", True,
                        f"enrichment={w.get('enrichment')} (vision is expected on 8002, embedding on 8003)")
    except httpx.HTTPError:
        check("wardrobe service is running on 8001", False, "start it with: uvicorn app.main:app --port 8001")
        return

    try:
        httpx.get(f"{WEATHER}/health", timeout=5).raise_for_status()
        all_ok &= check("weather service is running on 8004", True)
    except httpx.HTTPError:
        all_ok &= check("weather service is running on 8004", False,
                        "start it with: python -m uvicorn main:app --port 8004")

    r = httpx.get(f"{WARDROBE}/wardrobe/items", params={"user_id": user, "limit": 200}, timeout=10)
    if not check("GET /wardrobe/items still works", r.status_code == 200, f"status {r.status_code}"):
        return
    data = r.json()
    if not check("response still has 'items'", "items" in data):
        return
    items = data["items"]
    check(f"user '{user}' has clothes", bool(items), f"{len(items)} item(s)")

    needed = {"id", "category", "color", "material"}
    missing_fields = needed - set(items[0]) if items else set()
    all_ok &= check("items still have id, category, color, material", not missing_fields,
                    f"missing {sorted(missing_fields)}" if missing_fields else "")

    pending = [i for i in items if not i.get("category")]
    check("items with a category", True, f"{len(items) - len(pending)} tagged, {len(pending)} still pending")

    unknown = sorted({i["category"] for i in items if i.get("category") and i["category"] not in CATEGORY_MAP})
    all_ok &= check("every category is in CATEGORY_MAP", not unknown,
                    f"add these to CATEGORY_MAP in outfit_demo.py: {unknown}" if unknown else "")

    print("\nAll good, ready to connect." if all_ok else "\nFix the PROBLEM lines above, then run this again.")


if __name__ == "__main__":
    main()
