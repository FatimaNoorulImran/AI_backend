# Use a slim Python base — small image, fast Railway builds
FROM python:3.11-slim

# faster-whisper and edge-tts need ffmpeg for audio handling
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (separate layer = faster rebuilds when only code changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the rest of the app
COPY . .

# Make sure runtime folders exist even if .gitignore kept them out of the repo
RUN mkdir -p audio_files recordings

# Railway sets $PORT at runtime — don't hardcode 8000
ENV PORT=8000
EXPOSE 8000

CMD uvicorn main:app --host 0.0.0.0 --port $PORT