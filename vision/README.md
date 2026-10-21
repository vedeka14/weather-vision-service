# Vision service

Looks at a clothing photo and returns what it is, its colours and related details. It's built for wardrobe-ai: when a photo is uploaded there, wardrobe-ai calls this service and saves the answer with the item.

## How it works

1. **What is it?** Her trained YOLO model (`best.pt`, trained on 23 clothing types, 97% mAP50 on her validation set) finds the garment in the photo, e.g. "Kurti" with 0.88 confidence.
2. **What colour?** The service looks only inside the box the model drew, reduces it to its 6 main shades, and names them (navy, maroon, beige…). One colour covering 60% or more, with no busy print inside, means `solid`; otherwise `patterned`.
3. **The rest:** `material`, `style`, `occasion` and `season` come from a table per category (`CATEGORY_INFO` in main.py). For example, Jeans means denim, casual, and suits spring, autumn and winter. A photo can't reliably show fabric, so material is a sensible guess, or empty when the category doesn't tell you (e.g. Dress).

If several items are in the photo, clothing wins over accessories, then the most confident one. The others are listed in `attributes.other_items`.

## Setup (once)

1. **Get the model file.** Open https://github.com/Devanshi-Jhawar/wardrobe-ai/blob/main/runs/detect/train-2/weights/best.pt and click the download button (about 19 MB). Put it in this folder as `models\best.pt`.
2. **Install** (in PowerShell, in this `vision` folder). This downloads PyTorch, so it takes a few minutes:
   ```
   pip install -r requirements.txt
   ```

## Run it

```
python -m uvicorn main:app --reload --port 8002
```

Open http://localhost:8002/docs:
- **GET /health** shows `"model_loaded": true` when `models\best.pt` was found.
- **POST /analyze**: click Try it out, choose a photo and click Execute.

Example answer:

```json
{
  "category": "Shirt",
  "color": ["navy"],
  "pattern": "solid",
  "material": "cotton",
  "style": "smart casual",
  "occasion": ["office", "casual"],
  "season": ["summer", "spring", "autumn"],
  "attributes": {"confidence": 0.93, "box": [100, 80, 300, 350], "other_items": [], "color_shares": {"navy": 1.0}, "material_is_guess": true, "note": null}
}
```

If the model file is missing or nothing is recognised, `category` is empty, the colours of the whole photo are still returned, and `attributes.note` says why.

## Connecting to wardrobe-ai

Port 8002 and `POST /analyze` are exactly what wardrobe-ai expects (see [`integration/VISION-CONTRACT.md`](../integration/VISION-CONTRACT.md)).

1. Start vision on 8002.
2. Start an embedding service on 8003. Until hers exists, run the test stub: `python embed_stub.py`. **This matters:** wardrobe-ai calls vision and embedding together, and if embedding is down the upload is marked `failed` and the vision tags are lost.
3. In wardrobe-ai's `services\wardrobe\.env`, set `ENABLE_ENRICHMENT=true`, then start the wardrobe on 8001.
4. Upload a photo at http://localhost:8001/docs (POST /wardrobe/items) **without** `attributes_json`. The saved item should come back with `status: "ready"` and the category and colours filled in.

## Changing the rules

- Wrong material or occasion for a category: edit its line in `CATEGORY_INFO`.
- Colour names come from `color_name()`: it sorts by hue (red, orange, green…) and uses brightness for dark shades (navy, maroon, brown, olive). Change the hue cut-offs there to tune it.
- Too many wrong detections: raise `MIN_CONFIDENCE` (0.25 by default). Guesses between `WEAK_CONFIDENCE` (0.10) and that are only used when nothing better was found, and are flagged with `low_confidence: true`. `attributes.weak_guesses` always shows the model's unsure guesses.
