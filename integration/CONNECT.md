# Connecting the weather service to wardrobe-ai (later)

wardrobe-ai belongs to someone else (github.com/Devanshi-Jhawar/wardrobe-ai), so it isn't connected yet. Everything needed to connect it is saved here. The weather service is already built to be compatible.

Checked against wardrobe-ai on 2026-10-19 (commit on `main` at that date). Both services were run together, and outfits were picked from real wardrobe items. The weather data in that test was simulated.

## What's in this kit

| File | What it is |
|---|---|
| `weather/` folder | The `services/weather` folder for wardrobe-ai: main.py, outfit_demo.py, check_compat.py, requirements.txt, GUIDE.md |
| `add-weather-service.patch` | The same change as a git patch, including an update to wardrobe-ai's main README (Weather marked as built, plus how to run it) |
| `CONNECT.md` | This file |


## Why it's compatible

| wardrobe-ai expects | Weather service does |
|---|---|
| Wardrobe on port 8001, vision on 8002, embedding on 8003 | Runs on **8004**, so nothing clashes |
| Lists clothes at `GET /wardrobe/items?user_id=...`, returning `{"total", "items": [...]}` | `outfit_demo.py --user` reads exactly that |
| Each item has `category` (one of the 23 YOLO classes in data.yaml), `color` (list), `material`, `occasion`, `season` | `CATEGORY_MAP` in outfit_demo.py translates all 23 categories into the weather words (slot, type, warmth) |
| Items stay `pending` with no category until vision runs | Pending items are skipped, not errors |
| `material` can be empty | Rules still work without it |
| Accessories (Bag, Jewellery, Sunglasses, Dupatta) | Skipped for now |

No changes to wardrobe-ai's own code are needed.

## Category translation

| wardrobe-ai category | Slot | Weather type | Warmth |
|---|---|---|---|
| T-Shirt | top | t-shirt | light |
| Shirt | top | shirt | light |
| Kurti, Kameez | top | kurta | light |
| Hoodie | layer | hoodie | warm |
| Jacket | layer | jacket | warm |
| Blazer | layer | jacket | medium |
| Dress, Maxi, Saree | one-piece | dress | light |
| Anarkali, Lehenga | one-piece | dress | medium |
| Sherwani | one-piece | kurta | warm |
| Jeans | bottom | jeans | medium |
| Skirt | bottom | skirt | light |
| Shalwar, Sharara | bottom | trousers | light |
| Shoes | footwear | shoes | medium |
| Slippers | footwear | sandals | light |
| Dupatta, Bag, Jewellery, Sunglasses | accessory | (skipped) | |

If the YOLO model gets new classes, add them to `CATEGORY_MAP`. `check_compat.py` tells you which ones are missing.

## When you're ready to connect

1. **Check it still fits.** Clone the latest wardrobe-ai, start it on 8001, and upload a few clothes in http://localhost:8001/docs. Use `attributes_json` such as `{"category":"Kurti","color":["yellow"],"material":"cotton"}`. Start weather on 8004. Then, in the weather folder, run:
   ```
   python check_compat.py u1
   ```
   Every line should say OK. A PROBLEM line says what to fix.
2. **Try outfits:** `python outfit_demo.py Goa --user u1`
3. **Add it to the repo** (needs write access from the owner):
   - Copy the files from this repo's `weather` folder into `wardrobe-ai\services\weather\`, then:
   ```
   git checkout -b add-weather-service
   git add services/weather
   git commit -m "Add weather service"
   git push -u origin add-weather-service
   ```
   - Or apply the patch, which also updates the main README: `git apply add-weather-service.patch`
   - Open a pull request on GitHub.

## Things to watch in wardrobe-ai

- If they rename `category`, `color` or `material`, or change `/wardrobe/items`, `check_compat.py` will flag it. Update `from_wardrobe_item()` in outfit_demo.py to match.
- Once their vision service fills `material`, matching gets better automatically.
- Colours are free text (e.g. "navy"). Only "white" matters for the rain rule today.
- Their list endpoint filters `occasion` and `season` after paging, so with more than 200 items some could be missed. That's not an issue for a personal wardrobe.
