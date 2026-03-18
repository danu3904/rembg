import io
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import Response, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from rembg import remove, new_session
import uvicorn

# --------------------------------------------------------------------------- #
# Global session — lazy-initialized on first request                           #
# --------------------------------------------------------------------------- #
rembg_session = None

def get_session():
    global rembg_session
    if rembg_session is None:
        rembg_session = new_session("u2net")
    return rembg_session

# --------------------------------------------------------------------------- #
# Lifespan — warm-up model at startup (non-blocking crash)                    #
# --------------------------------------------------------------------------- #
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-warm the session so the first request isn't slow.
    # If this fails we log the error but don't crash the server.
    try:
        get_session()
        print("[rembg] u2net session initialised ✓")
    except Exception as exc:
        print(f"[rembg] WARNING: could not pre-warm session: {exc}")
    yield   # <-- server is running here

# --------------------------------------------------------------------------- #
# App                                                                          #
# --------------------------------------------------------------------------- #
app = FastAPI(
    title="AI Background Remover",
    description="Remove image backgrounds instantly using rembg + FastAPI.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Max upload size: 10 MB
MAX_FILE_BYTES = 10 * 1024 * 1024


# --------------------------------------------------------------------------- #
# Routes                                                                       #
# --------------------------------------------------------------------------- #
@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def read_index():
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if not os.path.exists(index_path):
        return JSONResponse(
            status_code=404,
            content={"error": "index.html not found. Ensure the static/ folder is present."},
        )
    return FileResponse(index_path)


@app.post("/remove-bg")
async def remove_background(file: UploadFile = File(...)):
    # 1. Validate MIME type
    if not file.content_type or not file.content_type.startswith("image/"):
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid file type: '{file.content_type}'. Please upload a JPG, PNG, or WebP image."},
        )

    # 2. Read and validate size
    content = await file.read()
    if len(content) > MAX_FILE_BYTES:
        return JSONResponse(
            status_code=400,
            content={"error": "File too large. Maximum allowed size is 10 MB."},
        )

    try:
        # 3. Remove background
        result = remove(content, session=get_session())
        return Response(content=result, media_type="image/png")

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"error": f"Processing failed: {str(exc)}"},
        )


# --------------------------------------------------------------------------- #
# Static files (CSS / JS assets if any)                                       #
# --------------------------------------------------------------------------- #
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# --------------------------------------------------------------------------- #
# Dev entry-point                                                              #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
