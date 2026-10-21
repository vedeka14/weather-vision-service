# Test results with the wardrobe-ai model

Photos run through `POST /analyze` on 2026-10-19. Shared so the model can be improved.

| Photo | Model said | Confidence | Verdict |
|---|---|---|---|
| Short sleeveless flared (peplum) kurti | Dress | 0.20 (flagged low) | Wrong: should be Kurti |
| Red and navy saree set (kurti + palazzo, collage) | Sharara | 0.90 | Right |
| Choker necklace on a velvet stand | Dupatta | 0.92 | Wrong: should be Jewellery |
| Chaniya choli | Anarkali | 0.91 | Close: should be Lehenga |
| Sea green peplum kurti with sharara | Sharara | 0.71 | Half right: missed the Kurti |
| Red sharara set | Sharara | 0.86 | Right |

## What this suggests for retraining

- Peplum / short flared kurtis are not recognised as Kurti (2 of 2 missed).
- Jewellery shown on a stand is read as Dupatta. Add product-style jewellery photos.
- Lehenga vs Anarkali gets mixed up.
- Sharara sets are recognised well.
