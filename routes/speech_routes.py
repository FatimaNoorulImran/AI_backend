"""
speech_routes.py
=================
Pronunciation-practice endpoints — ported from the old Main.py.

    POST /speak    -> TTS audio (English + Urdu)
    POST /check    -> STT + score + progress save
    POST /content  -> Teacher adds words
    GET  /content  -> Flutter fetches words
    GET  /progress/{child_name} -> Parent dashboard
"""

import os
import shutil
from datetime import date, datetime

from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import FileResponse

from services.speech_service import ai_speak, ai_check, ai_result, get_recording_path
from services.firebase_service import get_ref

router = APIRouter()


@router.post("/speak")
async def speak(data: dict):
    """
    Body: { "text": "Cat", "language": "english" }
    Response: mp3 audio file
    """
    language = data.get("language", "english")
    result = await ai_speak(data, language)

    if not result["success"]:
        return result

    return FileResponse(
        result["audio_path"],
        media_type="audio/mpeg",
        filename=os.path.basename(result["audio_path"])
    )


@router.post("/check")
async def check(
    audio: UploadFile = File(...),
    expected: str = Form(...),
    language: str = Form("english"),
    module_name: str = Form("General"),
    child_name: str = Form("Child"),
):
    """
    Form-data:
        audio       -> recording file
        expected    -> "Cat" or "بلی"
        language    -> "english" or "urdu"
        module_name -> "Animals"
        child_name  -> "Ali"
    """
    rec_path = get_recording_path()
    with open(rec_path, "wb") as f:
        shutil.copyfileobj(audio.file, f)

    check_result = ai_check(rec_path, expected, language)
    final_result = ai_result(check_result["score"])

    try:
        get_ref(f"progress/{child_name}/{module_name}").push({
            "word": expected,
            "score": check_result["score"],
            "correct": check_result["correct"],
            "heard": check_result["heard"],
            "language": language,
            "date": str(date.today()),
            "time": datetime.now().strftime("%H:%M"),
        })
        print(f"✅ Progress saved: {child_name} → {module_name} → {expected} → {check_result['score']}%")
    except Exception as e:
        print(f"⚠️ Progress save error: {e}")

    if os.path.exists(rec_path):
        os.remove(rec_path)

    return {**check_result, **final_result}


@router.post("/content")
async def add_content(data: dict):
    """
    Body:
        {
            "screen_name": "Animals",
            "type": "word",
            "language": "english",
            "items": ["Cat", "Dog", "Bird"]
        }
    """
    try:
        screen_name = data.get("screen_name", "unnamed")
        language = data.get("language", "english")

        get_ref(f"screens/{screen_name}").set(data)

        for item in data.get("items", []):
            await ai_speak(item, language)

        return {"success": True, "message": f"'{screen_name}' saved!"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.get("/content")
async def get_content():
    try:
        data = get_ref("screens").get()
        if not data:
            return {"success": True, "screens": []}
        return {"success": True, "screens": list(data.values())}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.get("/progress/{child_name}")
async def get_progress(child_name: str):
    try:
        data = get_ref(f"progress/{child_name}").get()
        if not data:
            return {"success": True, "progress": {}}
        return {"success": True, "progress": data}
    except Exception as e:
        return {"success": False, "message": str(e)}