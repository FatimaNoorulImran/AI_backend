"""
main.py
=======
FYP Backend — entrypoint.

Run locally:
    uvicorn main:app --reload

Run in production (Railway sets $PORT for you):
    uvicorn main:app --host 0.0.0.0 --port $PORT
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from dotenv import load_dotenv

from routes.avatar_routes import router as avatar_router
from routes.speech_routes import router as speech_router
from services.firebase_service import init_firebase

load_dotenv()

# =============================================
# APP SETUP
# =============================================
app = FastAPI(title="IDD Avatar Assistant API")

app.add_middleware(GZipMiddleware, minimum_size=100)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================
# FIREBASE SETUP
# =============================================
init_firebase()

# =============================================
# ROUTES
# =============================================
app.include_router(avatar_router)
app.include_router(speech_router)


@app.get("/health")
def health():
    return {"status": "running"}


# Local dev only — Railway runs uvicorn directly via the Dockerfile/Procfile
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)