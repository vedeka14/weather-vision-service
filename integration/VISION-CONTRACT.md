# Vision contract (what wardrobe-ai expects)

Looks at a clothing photo and returns its details. wardrobe-ai calls it on every upload when `ENABLE_ENRICHMENT=true`.

## The contract wardrobe-ai expects

From wardrobe-ai's `services/wardrobe/app/clients.py` and `config.py`:

- **Port:** 8002 (`VISION_SERVICE_URL=http://localhost:8002`)
- **Address:** `POST /analyze`, with the image sent as a multipart form field named `file`
- **Returns JSON** with these fields. wardrobe-ai saves exactly these and ignores anything else:

```json
{
  "category": "Kurti",
  "color": ["yellow"],
  "pattern": "solid",
  "material": "cotton",
  "style": "casual",
  "occasion": ["office", "casual"],
  "season": ["summer"],
  "attributes": {}
}
```

## Rules so it also works with the weather service

- **`category`** must be one of the 23 YOLO class names, spelled exactly as in wardrobe-ai's `data.yaml`: Anarkali, Bag, Blazer, Dress, Dupatta, Hoodie, Jacket, Jeans, Jewellery, Kameez, Kurti, Lehenga, Maxi, Saree, Shalwar, Sharara, Sherwani, Shirt, Shoes, Skirt, Slippers, Sunglasses, T-Shirt. The weather side's `CATEGORY_MAP` (outfit_demo.py) translates these.
- **`material`** should be one of the weather words: cotton, linen, rayon, polyester, denim, wool, fleece, leather, suede, silk, nylon. See `GET /weather/vocabulary`.
- **`color`** should be lowercase plain names (white, black, navy…). The rain rule checks for "white".
