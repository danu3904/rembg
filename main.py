import io
import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import Response, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from rembg import remove, new_session
from PIL import Image
import uvicorn

app = FastAPI(
    title="AI Background Remover",
    description="A simple but powerful background remover using rembg and FastAPI.",
    version="1.0.0"
)

# Enable CORS for frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Max file size: 10MB
IMAGE_SIZE_LIMIT = 10 * 1024 * 1024

# Pre-initialize rembg session with u2net model for better performance
# In the Dockerfile, we ensured this is pre-downloaded to U2NET_HOME
model_name = "u2net"
session = new_session(model_name)

# Ensure static directory exists
os.makedirs("static", exist_ok=True)

# Serve static files (frontend)
@app.get("/")
async def read_index():
    return FileResponse("static/index.html")

@app.post("/remove-bg")
async def remove_background(file: UploadFile = File(...)):
    # 1. Basic validation
    if not file.content_type.startswith("image/"):
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid file type: {file.content_type}. Please upload an image."}
        )
    
    # 2. Size validation
    content = await file.read()
    if len(content) > IMAGE_SIZE_LIMIT:
        return JSONResponse(
            status_code=400,
            content={"error": "File size too large. Maximum size is 10MB."}
        )
    
    try:
        # 3. Process the image
        # Use rembg with the pre-initialized session
        result = remove(content, session=session)
        
        # 4. Return as PNG
        return Response(content=result, media_type="image/png")
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Internal server error: {str(e)}"}
        )

# Mount static files (if there are other assets like JS/CSS)
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
