# Use Python 3.10 slim as base image
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV U2NET_HOME=/app/.u2net

WORKDIR /app

# libgl1 replaces libgl1-mesa-glx on newer Debian
# libgomp1 is required by onnxruntime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p $U2NET_HOME && \
    python -c "from rembg import new_session; new_session('u2net')" && \
    echo "Model downloaded successfully."

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
