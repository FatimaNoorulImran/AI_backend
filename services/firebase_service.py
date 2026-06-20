"""
firebase_service.py
====================
Centralizes Firebase Admin SDK setup so it only happens once,
and gives other modules a single place to import `db` from.
"""

import os
import firebase_admin
from firebase_admin import credentials, db

_initialized = False


def init_firebase():
    """Call once on app startup (from main.py)."""
    global _initialized
    if _initialized:
        return

    key_path = os.environ.get("FIREBASE_KEY_PATH", "serviceAccountKey.json")
    db_url = os.environ.get("FIREBASE_DB_URL")

    if not db_url:
        print("⚠️ FIREBASE_DB_URL not set — skipping Firebase init. "
              "Progress/content endpoints will fail until this is configured.")
        return

    if not os.path.exists(key_path):
        print(f"⚠️ {key_path} not found — skipping Firebase init.")
        return

    try:
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred, {"databaseURL": db_url})
        _initialized = True
        print("✅ Firebase connected!")
    except Exception as e:
        print(f"⚠️ Firebase init failed: {e}")


def get_ref(path: str):
    """Get a Firebase Realtime Database reference. Raises if Firebase isn't initialized."""
    if not _initialized:
        raise RuntimeError("Firebase is not initialized — check FIREBASE_DB_URL and serviceAccountKey.json")
    return db.reference(path)