# 🎨 AI Background Remover

A simple but powerful web application to remove image backgrounds instantly using **FastAPI** and **rembg** (u2net AI model).

![Preview](https://img.shields.io/badge/FastAPI-0.110-green?logo=fastapi) ![rembg](https://img.shields.io/badge/rembg-u2net-purple) ![Python](https://img.shields.io/badge/Python-3.10-blue?logo=python)

---

## ✨ Features

- **Drag & Drop** interface for easy image uploading
- **Side-by-side** before/after comparison
- **Download** the transparent PNG result
- **Fast processing** with ONNX Runtime (CPU-optimized)
- **Error handling** for invalid file types and oversized images (max 10MB)
- **Deployment ready** for Railway

---

## 📁 Project Structure

```
rembg/
├── main.py             # FastAPI backend
├── requirements.txt    # Python dependencies
├── Dockerfile          # Optimized Docker build
├── .dockerignore       # Docker ignore rules
├── .gitignore          # Git ignore rules
└── static/
    └── index.html      # Frontend UI
```

---

## 🚀 Running Locally

### 1. Create and activate a virtual environment

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**macOS / Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> ⚠️ **Note:** On first run, rembg will automatically download the `u2net` model (~170MB) to `~/.u2net/`. This only happens once.

### 3. Start the server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Open in browser

Navigate to: **[http://localhost:8000](http://localhost:8000)**

---

## 🐳 Running with Docker

### Build the image

```bash
docker build -t bg-remover .
```

> The Dockerfile pre-downloads the u2net model **at build time**, so the container starts instantly without any download delays.

### Run the container

```bash
docker run -p 8000:8000 bg-remover
```

Open: **[http://localhost:8000](http://localhost:8000)**

---

## ☁️ Deploy to Railway

### Prerequisites
- A [Railway account](https://railway.app)
- [Railway CLI](https://docs.railway.app/develop/cli) installed: `npm i -g @railway/cli`

### Steps

#### Option A: Via GitHub (Recommended)
1. Push this project to a GitHub repository.
2. Go to [Railway](https://railway.app/) → **New Project** → **Deploy from GitHub repo**.
3. Select your repository.
4. Railway will automatically detect the `Dockerfile` and deploy it.
5. Go to **Settings** → **Networking** → **Generate Domain** to get a public URL.

#### Option B: Via Railway CLI
```bash
# Login to Railway
railway login

# Initialize a new project
railway init

# Deploy
railway up
```

### Environment Variables (Optional)
You can set these in Railway's dashboard under **Variables**:

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT`   | `8000`  | Port to bind the server |

> **Note:** If Railway injects a `PORT` variable automatically, update `CMD` in `Dockerfile` to:
> ```dockerfile
> CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
> ```

---

## 🔌 API Reference

### `POST /remove-bg`

Remove the background from an uploaded image.

**Request:**
- Content-Type: `multipart/form-data`
- Body: `file` — the image file (JPG, PNG, WebP)

**Response:**
- `200 OK` — Returns a transparent PNG image
- `400 Bad Request` — Invalid file type or file too large
- `500 Internal Server Error` — Processing error

**Example with curl:**
```bash
curl -X POST "http://localhost:8000/remove-bg" \
  -F "file=@your-image.jpg" \
  --output result.png
```

**Example with Python:**
```python
import requests

with open("photo.jpg", "rb") as f:
    response = requests.post("http://localhost:8000/remove-bg", files={"file": f})

with open("result.png", "wb") as out:
    out.write(response.content)
```

---

## 🧰 Tech Stack

| Component | Technology |
|-----------|------------|
| Backend   | FastAPI + Uvicorn |
| AI Model  | rembg (u2net) |
| Runtime   | ONNX Runtime (CPU) |
| Frontend  | HTML + Tailwind CSS |
| Container | Docker |
| Hosting   | Railway |
