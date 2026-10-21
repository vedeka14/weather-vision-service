"""Vision service: looks at a clothing photo and returns its details.

wardrobe-ai calls POST /analyze on every upload (when ENABLE_ENRICHMENT=true)
and saves the returned fields with the item. See integration/VISION-CONTRACT.md for the contract.
"""
import colorsys
import io
import os
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image, ImageFilter, ImageStat, UnidentifiedImageError

app = FastAPI(title="Vision service")

# The YOLO model trained in wardrobe-ai (runs/detect/train-2/weights/best.pt).
MODEL_PATH = Path(os.environ.get("MODEL_PATH", Path(__file__).parent / "models" / "best.pt"))
MIN_CONFIDENCE = 0.25  # detections at least this sure are trusted
WEAK_CONFIDENCE = 0.10  # below MIN but at least this: used only if nothing better, and flagged
PATTERN_EDGES = 15  # edge score above this means printed/patterned (plain fabric scores about 0-5)

# What each YOLO category usually means for the other fields. Vision can't see
# fabric reliably from a photo, so material is a sensible default (None = unknown).
# Material words match the weather service's vocabulary.
CATEGORY_INFO = {
    "T-Shirt":  {"material": "cotton", "style": "casual", "occasion": ["casual"], "season": ["summer", "spring"]},
    "Shirt":    {"material": "cotton", "style": "smart casual", "occasion": ["office", "casual"], "season": ["summer", "spring", "autumn"]},
    "Kurti":    {"material": "cotton", "style": "ethnic", "occasion": ["casual", "office"], "season": ["summer", "spring"]},
    "Kameez":   {"material": "cotton", "style": "ethnic", "occasion": ["casual", "festival"], "season": ["summer", "spring"]},
    "Hoodie":   {"material": "fleece", "style": "casual", "occasion": ["casual", "trip"], "season": ["winter", "autumn"]},
    "Jacket":   {"material": None, "style": "casual", "occasion": ["casual", "trip"], "season": ["winter", "autumn"]},
    "Blazer":   {"material": None, "style": "formal", "occasion": ["office", "party"], "season": ["autumn", "winter", "spring"]},
    "Dress":    {"material": None, "style": "casual", "occasion": ["casual", "party"], "season": ["summer", "spring"]},
    "Maxi":     {"material": None, "style": "casual", "occasion": ["casual", "trip"], "season": ["summer", "spring"]},
    "Saree":    {"material": None, "style": "ethnic", "occasion": ["festival", "wedding", "office"], "season": ["summer", "spring", "autumn"]},
    "Anarkali": {"material": None, "style": "ethnic", "occasion": ["festival", "wedding"], "season": ["spring", "autumn", "winter"]},
    "Lehenga":  {"material": None, "style": "ethnic", "occasion": ["wedding", "festival"], "season": ["autumn", "winter"]},
    "Sherwani": {"material": None, "style": "ethnic", "occasion": ["wedding", "festival"], "season": ["autumn", "winter"]},
    "Jeans":    {"material": "denim", "style": "casual", "occasion": ["casual", "trip"], "season": ["spring", "autumn", "winter"]},
    "Skirt":    {"material": None, "style": "casual", "occasion": ["casual", "party"], "season": ["summer", "spring"]},
    "Shalwar":  {"material": "cotton", "style": "ethnic", "occasion": ["casual", "festival"], "season": ["summer", "spring"]},
    "Sharara":  {"material": None, "style": "ethnic", "occasion": ["festival", "wedding"], "season": ["spring", "autumn"]},
    "Shoes":    {"material": None, "style": "casual", "occasion": ["casual", "office"], "season": ["spring", "autumn", "winter"]},
    "Slippers": {"material": None, "style": "casual", "occasion": ["casual"], "season": ["summer"]},
    "Dupatta":  {"material": None, "style": "ethnic", "occasion": ["festival", "casual"], "season": ["summer", "spring", "autumn"]},
    "Bag":      {"material": None, "style": "accessory", "occasion": ["casual", "office", "trip"], "season": []},
    "Jewellery": {"material": None, "style": "accessory", "occasion": ["festival", "wedding", "party"], "season": []},
    "Sunglasses": {"material": None, "style": "accessory", "occasion": ["casual", "trip"], "season": ["summer"]},
}
ACCESSORIES = {"Bag", "Jewellery", "Sunglasses", "Dupatta"}

_model = None


def load_model():
    """Load the YOLO model once. Returns None if the file isn't there yet."""
    global _model
    if _model is None and MODEL_PATH.exists():
        from ultralytics import YOLO  # imported here so the service starts even without it
        _model = YOLO(str(MODEL_PATH))
    return _model


def color_name(rgb):
    """Name a colour the way a person would, from its hue, strength and brightness.

    Works on hue rather than "closest RGB" so dark shades keep their colour:
    a bottle-green kurti is "green", not "black".
    """
    h, s, v = colorsys.rgb_to_hsv(*(c / 255 for c in rgb))
    hue = h * 360
    if v < 0.12:
        return "black"
    if s < 0.15 or (s < 0.25 and v < 0.25):  # no real colour: black, grey or white
        return "white" if v > 0.85 else "black" if v < 0.25 else "grey"
    if hue < 15 or hue >= 345:
        return "maroon" if v < 0.5 else "pink" if s < 0.45 and v > 0.7 else "red"
    if hue < 40:
        return "brown" if v < 0.6 else "beige" if s < 0.45 else "orange"
    if hue < 65:
        return "olive" if v < 0.6 else "beige" if s < 0.45 else "yellow"
    if hue < 160:
        return "olive" if hue < 75 and v < 0.6 else "green"
    if hue < 200:
        return "teal"
    if hue < 250:
        return "navy" if v < 0.45 else "light blue" if s < 0.45 and v > 0.7 else "blue"
    if hue < 290:
        return "purple"
    return "purple" if v < 0.5 else "pink"


def colors_and_pattern(img):
    """Main colours of the garment, plus a rough solid/patterned guess."""
    # Use the centre of the crop so background around the garment counts less.
    w, h = img.size
    centre = img.crop((w * 0.2, h * 0.2, w * 0.8, h * 0.8)).convert("RGB")
    img = centre.resize((64, 64))
    quant = img.quantize(colors=6)
    palette = quant.getpalette()
    counts = sorted(quant.getcolors(), reverse=True)  # [(pixel_count, palette_index), ...]
    total = sum(c for c, _ in counts)

    shares = {}
    for count, idx in counts:
        name = color_name(tuple(palette[idx * 3: idx * 3 + 3]))
        shares[name] = shares.get(name, 0) + count / total
    ranked = sorted(shares.items(), key=lambda kv: kv[1], reverse=True)

    colors = [name for name, share in ranked if share >= 0.2][:2] or [ranked[0][0]]
    # Small prints in one colour family (e.g. green motifs on green) don't change the
    # colour names, so also look for lots of sharp edges inside the garment.
    edges = centre.convert("L").resize((128, 128)).filter(ImageFilter.FIND_EDGES).crop((2, 2, 126, 126))
    busy = ImageStat.Stat(edges).mean[0] > PATTERN_EDGES
    pattern = "solid" if ranked[0][1] >= 0.6 and not busy else "patterned"
    return colors, pattern, {name: round(share, 2) for name, share in ranked}


def detect(img):
    """Run the clothing model. Returns detections sorted best first."""
    model = load_model()
    if model is None:
        return None
    # YOLO drops anything under 0.25 by default; ask for weaker guesses too.
    result = model(img, conf=0.05, verbose=False)[0]
    found = []
    for box in result.boxes:
        found.append({
            "category": result.names[int(box.cls[0])],
            "confidence": round(float(box.conf[0]), 2),
            "box": [round(v) for v in box.xyxy[0].tolist()],
        })
    # Prefer clothing over accessories, then the most confident one.
    found.sort(key=lambda d: (d["category"] in ACCESSORIES, -d["confidence"]))
    return found


@app.get("/health")
def health():
    return {"ok": True, "model_loaded": load_model() is not None, "model_path": str(MODEL_PATH)}


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    raw = await file.read()
    try:
        img = Image.open(io.BytesIO(raw))
        if img.mode in ("RGBA", "LA", "P"):
            # Transparent PNGs: put them on white, otherwise the see-through parts turn black.
            img = img.convert("RGBA")
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background
        else:
            img = img.convert("RGB")
    except (UnidentifiedImageError, OSError):
        raise HTTPException(400, "File is not a valid image.")

    all_found = detect(img)
    detections = None if all_found is None else [d for d in all_found if d["confidence"] >= MIN_CONFIDENCE]
    weak = [d for d in (all_found or []) if d["confidence"] < MIN_CONFIDENCE]
    weak.sort(key=lambda d: -d["confidence"])

    main = detections[0] if detections else None
    low_confidence = False
    if main is None and weak and weak[0]["confidence"] >= WEAK_CONFIDENCE:
        main, low_confidence = weak[0], True

    # Colours come from the detected garment only, or the whole photo if nothing was found.
    garment = img.crop(tuple(main["box"])) if main else img
    colors, pattern, color_shares = colors_and_pattern(garment)

    category = main["category"] if main else None
    info = CATEGORY_INFO.get(category, {"material": None, "style": None, "occasion": [], "season": []})

    if detections is None:
        note = f"Model file not found at {MODEL_PATH}. Only colours were analysed."
    elif low_confidence:
        note = f"Low confidence ({main['confidence']}): please check the category."
    elif not detections:
        note = "No clothing recognised. Only colours were analysed."
    else:
        note = None

    return {
        "category": category,
        "color": colors,
        "pattern": pattern,
        "material": info["material"],
        "style": info["style"],
        "occasion": info["occasion"],
        "season": info["season"],
        "attributes": {
            "confidence": main["confidence"] if main else None,
            "low_confidence": low_confidence,
            "weak_guesses": [f"{d['category']} {d['confidence']}" for d in weak[:3]],
            "box": main["box"] if main else None,
            "other_items": sorted({d["category"] for d in (detections or [])[1:]} - {category}),
            "color_shares": color_shares,
            "material_is_guess": info["material"] is not None,
            "note": note,
        },
    }
