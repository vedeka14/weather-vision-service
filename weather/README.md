# Weather service

A tiny web service that gives a short forecast (default: Goa, next 4 days) with a hot / mild / cold label per day. Data comes free from Open-Meteo, no key needed.

## Run it

Open a terminal in this `weather` folder, then:

```
pip install -r requirements.txt
uvicorn main:app --reload --port 8004
```

Wait for "Application startup complete", then open http://localhost:8004/docs in your browser.

## Try it

- http://localhost:8004/weather gives 4 days for Goa
- http://localhost:8004/weather?days=7 gives 7 days
- http://localhost:8004/weather?lat=28.61&lon=77.21 gives Delhi
- http://localhost:8004/weather?city=Manali searches by city name
- http://localhost:8004/weather?city=Goa&start_date=2026-10-20&end_date=2026-10-23 plans a trip (dates up to 16 days ahead)

- http://localhost:8004/weather/vocabulary lists the clothing words (types, materials, warmth) the service uses

Each day also has `rainy` (rain chance 60% or more) and `needs`: what the weather asks of an outfit (warmth, sleeves, types and materials to prefer or avoid, waterproof, evening layer, accessories). It doesn't pick clothes; the gap agent matches `needs` against the user's wardrobe, and anything missing becomes a buying suggestion. The `trip` block rolls all days up for packing.

The vision service should tag uploaded clothes with the same words as `/weather/vocabulary`, so matching is a simple lookup.

Python 3.10 or newer is needed.

Labels: hot if the max is 32°C or more, cold if under 20°C, mild otherwise.

## Using it with wardrobe-ai

The wardrobe service (github.com/Devanshi-Jhawar/wardrobe-ai) runs on port 8001 and expects vision on 8002 and embedding on 8003, so weather runs on **8004**.

With both running, `python outfit_demo.py Goa --user u1` reads user u1's clothes from the wardrobe and picks outfits for the Goa forecast. `CATEGORY_MAP` in outfit_demo.py translates each wardrobe category (Kurti, Saree, Jeans…) into the weather vocabulary. Items still "pending" (no category yet) and accessories are skipped.
