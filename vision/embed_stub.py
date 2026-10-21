"""TEST ONLY: a fake embedding service on port 8003.

wardrobe-ai calls vision AND embedding on every upload. If embedding isn't
running, the upload is marked "failed" and the vision tags are thrown away.
Run this until the real embedding service exists:  python embed_stub.py
"""
import uvicorn
from fastapi import FastAPI, File, UploadFile

app = FastAPI(title="Embedding stub (test only)")


@app.post("/embed")
async def embed(file: UploadFile = File(...)):
    return {"embedding": [0.0] * 8}


if __name__ == "__main__":
    uvicorn.run(app, port=8003)
