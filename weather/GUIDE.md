# The weather service, explained in detail

This guide explains everything you see at **http://localhost:8004**: what it is, how a request travels through it, every input and output, the clothing rules, the errors, and the code line by line.

---

## 1. The big picture

The weather service is a **tiny website that runs on your own computer**. It doesn't show pages for people to read. Instead it answers questions with data, so other programs (your agents) can use it. A website like this is called an **API**.

- **localhost** means "this computer". Nobody else can see it.
- **8004** is the **port**, a numbered door on your computer. Each service gets its own door. Wardrobe uses 8001, vision 8002, embedding 8003 and weather 8004. These are the ports wardrobe-ai expects.
- **uvicorn** is the program that keeps the service running and listens at that door. That's why PowerShell must stay open.
- **FastAPI** is the Python library the code is written with. It also creates the `/docs` page for free.
- **Open-Meteo** is the free weather website the service gets its forecasts from.

The weather service's one job in your wardrobe app:

> Given a place and some dates, say **what kind of clothes the weather calls for** on each day.

It does **not** choose clothes from the wardrobe. That's the gap agent's job (see section 9).

---

## 2. What happens when you open /weather

Say you open `http://localhost:8004/weather?city=Goa&days=4`.

1. **Your browser** sends the request to door 8004 on your computer.
2. **uvicorn** receives it and hands it to **FastAPI**.
3. **FastAPI** sees the address is `/weather`, so it runs the `weather()` function in `main.py`. It reads `city=Goa` and `days=4` from the address and checks they're valid. For example, `days` must be a whole number from 1 to 16.
4. Because a **city** was given, the code first asks **Open-Meteo's place search**: "Where is Goa?" The answer is coordinates (latitude and longitude) and a proper name, such as "Panaji, India".
5. The code works out the **dates**: today plus the next 3 days. It checks they're not in the past and not more than 16 days ahead.
6. It asks **Open-Meteo's forecast** for those coordinates and dates: the daily high, low and rain chance.
7. For **each day** it adds:
   - a **label**: hot, mild or cold
   - **rainy**: yes or no
   - **needs**: what the outfit should be like
8. It adds a **trip** summary covering all the days.
9. FastAPI sends everything back as **JSON** (a neat text format for data), and your browser shows it.

All of this takes about a second.

---

## 3. The /docs page (your control panel)

Open **http://localhost:8004/docs**. FastAPI builds this page automatically from the code. It lists every address and lets you try each one without typing URLs.

How to use it:

1. Click a row, for example **GET /weather**.
2. Click **Try it out**. The input boxes become editable.
3. Fill in the boxes you want, for example city = `Goa`. Leave the others empty.
4. Click **Execute**.
5. Scroll down to **Server response**:
   - **Code** is the result code. **200** means success.
   - **Response body** is the actual answer (the JSON).
   - **Request URL** is the full address it called. You can copy it into a browser tab to get the same answer directly.

The section below that, **Responses** (with "Example Value: string" and "422 Validation Error"), is **only documentation**. It describes what *could* come back. It is not your result, so it's normal for it to look generic.

The **Schemas** box at the very bottom describes the format of error messages. You can ignore it.

**GET** in the coloured badge means "this address only reads data, it doesn't change anything".

---

## 4. The three addresses

| Address | What it does | Example |
|---|---|---|
| `/health` | Says the service is alive. Returns `{"ok": true}`. Useful later when one service checks another is running. | http://localhost:8004/health |
| `/weather/vocabulary` | Lists the exact clothing words the service uses: **types** (t-shirt, jeans, sandals…), **materials** (cotton, wool…) and **warmth** (light, medium, warm, very_warm). The vision and wardrobe services should tag clothes with these same words, so everything matches. | http://localhost:8004/weather/vocabulary |
| `/weather` | The main one: forecast plus clothing needs. | http://localhost:8004/weather?city=Goa |

---

## 5. Inputs for /weather

All inputs are optional. They go after a `?` in the address, joined with `&`.

| Input | Meaning | Default | Allowed |
|---|---|---|---|
| `city` | Place name. If given, `lat` and `lon` are ignored. | none | Any name Open-Meteo knows, e.g. Goa, Manali, Mumbai, Paris |
| `lat` | Latitude, how far north the place is | 15.2993 (Goa) | Any number |
| `lon` | Longitude, how far east the place is | 74.124 (Goa) | Any number |
| `days` | How many days to show, starting from `start_date` | 4 | 1 to 16 |
| `start_date` | First day | today | A date like `2026-10-20`, not in the past |
| `end_date` | Last day | `start_date` + `days` − 1 | On or after `start_date`, within 16 days of today |

Examples you can paste into your browser:

- Goa, next 4 days: `http://localhost:8004/weather`
- Goa, a whole week: `http://localhost:8004/weather?days=7`
- Delhi by coordinates: `http://localhost:8004/weather?lat=28.61&lon=77.21`
- Manali by name: `http://localhost:8004/weather?city=Manali`
- A trip on specific dates: `http://localhost:8004/weather?city=Goa&start_date=2026-10-20&end_date=2026-10-23`

Why only 16 days? Open-Meteo can't forecast further than that, and nobody can forecast weather reliably beyond about two weeks.

When you search by city, always glance at `place` in the answer. Some names exist in several countries, and the search picks the most likely one.

---

## 6. The output, field by field

Here's a real-shaped answer for Goa, showing two days. The numbers are from your own run earlier.

```json
{
  "place": "Panaji, India",
  "timezone": "Asia/Kolkata",
  "days": [
    {
      "date": "2026-10-15",
      "max": 37.1,
      "min": 22.0,
      "rain_chance": 2,
      "label": "hot",
      "rainy": false,
      "needs": {
        "warmth": "light",
        "sleeves": "short",
        "types_prefer": ["t-shirt", "shirt", "top", "kurta", "dress", "skirt", "shorts", "sandals"],
        "types_avoid": ["sweater", "hoodie", "jacket", "coat", "boots"],
        "materials_prefer": ["cotton", "linen", "rayon"],
        "materials_avoid": ["wool", "fleece", "leather", "denim"],
        "colors_prefer": ["light"],
        "colors_avoid": [],
        "waterproof": false,
        "layer_for_evening": false,
        "accessories": ["sunglasses", "cap or hat", "sunscreen"]
      }
    },
    {
      "date": "2026-10-17",
      "max": 30.0,
      "min": 25.2,
      "rain_chance": 83,
      "label": "mild",
      "rainy": true,
      "needs": {
        "warmth": "medium",
        "sleeves": "any",
        "types_prefer": ["t-shirt", "shirt", "top", "kurta", "dress", "jeans", "trousers", "sneakers"],
        "types_avoid": ["coat"],
        "materials_prefer": ["cotton", "linen", "rayon", "polyester", "nylon"],
        "materials_avoid": ["fleece", "suede", "silk"],
        "colors_prefer": [],
        "colors_avoid": ["white"],
        "waterproof": true,
        "layer_for_evening": false,
        "accessories": ["umbrella or raincoat"]
      }
    }
  ],
  "trip": {
    "warmth_levels": ["light", "medium"],
    "rainy_days": 1,
    "needs_evening_layer": false,
    "needs_waterproof": true,
    "accessories": ["cap or hat", "sunglasses", "sunscreen", "umbrella or raincoat"]
  }
}
```

### Top level

| Field | Meaning |
|---|---|
| `place` | Where the forecast is for. The real place name when you used `city`, or the coordinates otherwise. |
| `timezone` | The local timezone of that place. Dates follow local time, so a trip to London shows London dates. |
| `days` | A list with one entry per day. |
| `trip` | A summary of all the days together, for packing. |

### Each day

| Field | Meaning |
|---|---|
| `date` | The day, in year-month-day format. |
| `max` | Highest temperature that day, in °C. |
| `min` | Lowest temperature, usually at night or early morning, in °C. |
| `rain_chance` | Highest chance of rain during the day, in %. |
| `label` | **hot** if `max` is 32 or above, **cold** if `max` is below 20, otherwise **mild**. |
| `rainy` | **true** if `rain_chance` is 60% or more. |
| `needs` | What that day's outfit should be like. See below. |

### Inside `needs`

| Field | Meaning | How the gap agent uses it |
|---|---|---|
| `warmth` | How warm the clothes should be: light, medium, warm or very_warm | Gives a bonus to clothes with the same warmth |
| `sleeves` | short, long or any | Preference for tops |
| `types_prefer` | Kinds of clothes that suit the day | Bonus points |
| `types_avoid` | Kinds of clothes that don't suit it | Removed completely |
| `materials_prefer` | Fabrics that suit the day | Bonus points |
| `materials_avoid` | Fabrics that don't suit it | Removed completely |
| `colors_prefer` | e.g. "light" colours on hot days (they stay cooler) | Bonus points |
| `colors_avoid` | e.g. white on rainy days (it shows mud and goes see-through) | Removed completely |
| `waterproof` | true on rainy days | Leather and suede shoes removed |
| `layer_for_evening` | true if nights get cool (below 18°C on mild days, always on cold days) | Adds a sweater or jacket to the outfit |
| `accessories` | Things to carry: sunglasses, umbrella, scarf… | Shown next to the outfit |

### Inside `trip`

| Field | Meaning |
|---|---|
| `warmth_levels` | Every warmth level needed across the trip. For example light and medium means pack mostly light clothes plus a few medium ones. |
| `rainy_days` | How many days are rainy |
| `needs_evening_layer` | Pack at least one sweater or jacket |
| `needs_waterproof` | Pack waterproof shoes or an umbrella |
| `accessories` | Every accessory needed on any day |

---

## 7. The clothing rules

These are simple **if-then rules**, written in the `clothing_needs` function. They're easy to change: edit the lists in `main.py`.

### By temperature (based on the day's high)

| | Hot (32°C and up) | Mild (20–31.9°C) | Cold (below 20°C) | Very cold (below 10°C) |
|---|---|---|---|---|
| Warmth | light | medium | warm | very_warm |
| Sleeves | short | any | long | long |
| Prefer types | t-shirt, shirt, top, kurta, dress, skirt, shorts, sandals | t-shirt, shirt, top, kurta, dress, jeans, trousers, sneakers | sweater, hoodie, jacket, jeans, trousers, shoes, boots | same as cold, plus coat |
| Avoid types | sweater, hoodie, jacket, coat, boots | coat | shorts, sandals, skirt | shorts, sandals, skirt |
| Prefer materials | cotton, linen, rayon | cotton, linen, denim, rayon | wool, fleece, denim | wool, fleece, denim |
| Avoid materials | wool, fleece, leather, denim | fleece | linen | linen |
| Evening layer | no | only if the low is below 18°C | yes | yes |
| Accessories | sunglasses, cap or hat, sunscreen | none | none | scarf, gloves |

### Extra rules when it's rainy (60% or more)

- `waterproof` becomes true.
- Quick-dry materials (polyester, nylon) are added to the preferred list, and denim is removed from it because it stays wet for hours.
- Suede and silk are added to the avoid list, because rain ruins them.
- White is added to `colors_avoid`.
- An umbrella or raincoat is added to accessories.

---

## 8. Errors and what they mean

The service always explains what went wrong in a `detail` message.

| Code | Meaning | Example cause | What to do |
|---|---|---|---|
| **200** | Success | | |
| **400** | Your dates don't work | `start_date` in the past, `end_date` before `start_date`, or dates more than 16 days ahead | Fix the dates. The message says the last allowed date. |
| **404** | City not found | `city=Nowhereville` | Check the spelling or use `lat` and `lon` |
| **422** | Input in the wrong format | `days=abc`, `days=20`, `start_date=20th Oct` | Use numbers for days (1 to 16) and dates like `2026-10-20` |
| **502** | Open-Meteo refused the request | Rare. Usually odd coordinates. | Read the reason in the message |
| **503** | Open-Meteo can't be reached | No internet, or Open-Meteo is down | Check your internet and try again |

These clear messages matter for the agents. The critic or planner can read "city not found" and ask the user again, instead of crashing.

---

## 9. How it fits into the wardrobe app

```
User: "4-day trip to Goa next week, what should I wear?"
        │
   Planner agent ── works out: city = Goa, dates = 20–23 Oct
        │
   Context agent ── calls /weather?city=Goa&start_date=...&end_date=...
        │              gets each day's "needs"
   Wardrobe ─────── the user's clothes, each tagged by the vision service
        │              with type, material, colour and warmth
   Gap agent ────── for each day and each slot (top, bottom, shoes):
        │              1. remove clothes the needs say to avoid
        │              2. score the rest: preferred type +2, preferred material +2, same warmth +1
        │              3. pick the best item; if nothing is left, suggest something to buy
   Composer ─────── adds the occasion (office, festival, trip) and the user's preferences
        │
   Critic ───────── checks the outfit; if it fails, sends it back to try again
```

`outfit_demo.py` in this folder is a working example of the gap agent step, using a 7-item sample wardrobe. Run it in a second PowerShell window while the weather service is running:

```
python outfit_demo.py Goa
```

---

## 10. The code, section by section (`main.py`)

| Part | What it does |
|---|---|
| `import ...` | Loads the tools: dates, `httpx` (calls other websites) and FastAPI. |
| `app = FastAPI(...)` | Creates the web service. `uvicorn main:app` means "run the `app` in `main.py`". |
| `FORECAST_URL`, `GEOCODE_URL` | The two Open-Meteo addresses: forecast, and place search. |
| `MAX_DAYS_AHEAD = 16` | The forecast limit, kept in one place. |
| `@app.get("/health")` | The `@app.get(...)` line above a function connects that function to an address. |
| `call_open_meteo()` | Calls Open-Meteo and turns any problem into a clear error (503 or 502) instead of a crash. It waits at most 10 seconds. |
| `find_city()` | Turns a city name into coordinates using the place search. Returns 404 if nothing is found. |
| `temperature_label()` | The hot, mild or cold rule. |
| `TYPES`, `MATERIALS`, `WARMTH` | The shared clothing vocabulary. |
| `clothing_needs()` | The rules in section 7. Takes the high, the low and whether it's rainy, and returns the `needs`. |
| `trip_summary()` | Combines all the days' needs into the `trip` block. |
| `@app.get("/weather/vocabulary")` | Returns the vocabulary lists. |
| `@app.get("/weather")` | The main function. Reads your inputs (FastAPI checks types and limits, which is where 422 errors come from), finds the city, works out and checks the dates, calls the forecast, then builds each day and the trip summary. |

---

## 11. Glossary

- **API**: a website meant for programs, not people. It answers with data.
- **Endpoint / address / route**: one URL of the API, such as `/weather`.
- **Query parameters**: the inputs after `?` in a URL, such as `?city=Goa&days=7`.
- **JSON**: the text format of the answers. `{ }` holds named fields and `[ ]` holds lists.
- **localhost:8004**: this computer, door 8004.
- **Status code**: a number saying how the request went. 200 is OK, 4xx means a problem with the input, 5xx means a problem on the server or weather site.
- **uvicorn**: the program that runs the service. Stop it with Ctrl+C.
- **`--reload`**: makes uvicorn restart automatically when you save `main.py`.
