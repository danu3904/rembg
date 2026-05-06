import io
import os
import zipfile
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import Response, FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from rembg import remove, new_session
from PIL import Image
import uvicorn

# Global session — di-load saat pertama kali dipanggil
rembg_session = None
executor = ThreadPoolExecutor(max_workers=4)

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

app = FastAPI(title="AI Background Remover + WhatsApp Sticker", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STICKER_SIZE = 512
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# --- Helper Functions ---

def process_remove_bg(image_bytes: bytes, sticker_mode: bool = False) -> bytes:
    """Remove background and optionally resize to sticker dimensions."""
    result = remove(image_bytes, session=get_session())
    
    if sticker_mode:
        img = Image.open(io.BytesIO(result))
        
        # Convert to RGBA if not already
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Resize to fit within 512x512 while maintaining aspect ratio
        img.thumbnail((STICKER_SIZE, STICKER_SIZE), Image.LANCZOS)
        
        # Create new 512x512 image with transparent background
        new_img = Image.new('RGBA', (STICKER_SIZE, STICKER_SIZE), (0, 0, 0, 0))
        
        # Center the image
        x = (STICKER_SIZE - img.width) // 2
        y = (STICKER_SIZE - img.height) // 2
        new_img.paste(img, (x, y), img)
        
        # Save to bytes
        output = io.BytesIO()
        new_img.save(output, format='PNG', optimize=True)
        return output.getvalue()
    
    return result

def process_file_sync(content: bytes, sticker_mode: bool = False) -> bytes:
    """Synchronous wrapper for processing."""
    return process_remove_bg(content, sticker_mode=sticker_mode)

# --- Endpoints ---

@app.get("/health")
async def health():
    return {"status": "ok", "features": ["remove-bg", "batch", "sticker"]}

@app.get("/")
async def read_index():
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if not os.path.exists(index_path):
        return JSONResponse(status_code=404, content={"error": "index.html not found"})
    return FileResponse(index_path)

@app.post("/remove-bg")
async def remove_background(
    file: UploadFile = File(...),
    mode: str = Form("normal")  # "normal" or "sticker"
):
    """Remove background from single image."""
    if not file.content_type or not file.content_type.startswith("image/"):
        return JSONResponse(status_code=400, content={"error": "Bukan file gambar"})
    
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        return JSONResponse(status_code=400, content={"error": "File terlalu besar (>10MB)"})

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor, process_file_sync, content, mode == "sticker"
        )
        media_type = "image/png"
        if mode == "sticker":
            # Suggest filename for sticker
            headers = {"Content-Disposition": f'attachment; filename="sticker_{file.filename or "image"}.png"'}
            return Response(content=result, media_type=media_type, headers=headers)
        return Response(content=result, media_type=media_type)
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})

@app.post("/remove-bg-batch")
async def remove_background_batch(
    files: list[UploadFile] = File(...),
    mode: str = Form("normal")
):
    """Remove background from multiple images. Returns ZIP file."""
    if not files:
        return JSONResponse(status_code=400, content={"error": "Tidak ada file yang diupload"})
    
    if len(files) > 20:
        return JSONResponse(status_code=400, content={"error": "Maksimal 20 gambar sekaligus"})

    processed_files = []
    errors = []
    
    for idx, file in enumerate(files):
        if not file.content_type or not file.content_type.startswith("image/"):
            errors.append({"file": file.filename or f"file_{idx}", "error": "Bukan file gambar"})
            continue
        
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            errors.append({"file": file.filename or f"file_{idx}", "error": "File terlalu besar (>10MB)"})
            continue
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                executor, process_file_sync, content, mode == "sticker"
            )
            
            # Generate filename
            base_name = os.path.splitext(file.filename or f"image_{idx}")[0]
            suffix = "_sticker" if mode == "sticker" else "_nobg"
            out_name = f"{base_name}{suffix}.png"
            
            processed_files.append((out_name, result))
        except Exception as exc:
            errors.append({"file": file.filename or f"file_{idx}", "error": str(exc)})

    if not processed_files:
        return JSONResponse(status_code=400, content={
            "error": "Tidak ada gambar yang berhasil diproses",
            "details": errors
        })

    # Create ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in processed_files:
            zf.writestr(name, data)

    zip_buffer.seek(0)
    headers = {
        "Content-Disposition": 'attachment; filename="batch_results.zip"',
        "X-Processed-Count": str(len(processed_files)),
        "X-Error-Count": str(len(errors))
    }
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers=headers
    )

@app.post("/sticker")
async def create_sticker(file: UploadFile = File(...)):
    """Create WhatsApp sticker (512x512 transparent PNG)."""
    return await remove_background(file, mode="sticker")

@app.post("/sticker-batch")
async def create_sticker_batch(files: list[UploadFile] = File(...)):
    """Create multiple WhatsApp stickers. Returns ZIP file."""
    return await remove_background_batch(files, mode="sticker")

# Mount folder static
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
