import io
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import Response, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from rembg import remove, new_session
import uvicorn

# Global session — di-load saat pertama kali dipanggil
rembg_session = None

def get_session():
    global rembg_session
    if rembg_session is None:
        rembg_session = new_session("u2net")
    return rembg_session

# Startup events
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        get_session()
        print("[rembg] u2net session initialized")
    except Exception as exc:
        print(f"[rembg] Warning: {exc}")
    yield

app = FastAPI(title="AI Background Remover", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/")
async def read_index():
    # Menggunakan absolute path agar Railway selalu menemukan file
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if not os.path.exists(index_path):
        return JSONResponse(status_code=404, content={"error": "index.html not found"})
    return FileResponse(index_path)

@app.post("/remove-bg")
async def remove_background(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        return JSONResponse(status_code=400, content={"error": "Bukan file gambar"})
    
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        return JSONResponse(status_code=400, content={"error": "File terlalu besar (>10MB)"})

    try:
        result = remove(content, session=get_session())
        return Response(content=result, media_type="image/png")
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})

# Mount folder static
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
