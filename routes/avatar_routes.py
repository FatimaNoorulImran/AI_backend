from fastapi import APIRouter
from fastapi.responses import Response
from services.intent_parser import parse_intent
from models.request_models import AvatarRequest, AvatarResponse
from services.ai_service import get_avatar_response

router = APIRouter()

# Expression map — what face the avatar shows
EXPRESSIONS: dict[str, str] = {
    "correct_answer": "celebrating",
    "wrong_answer":   "encouraging",
    "voice_command":  "happy",
    "game_complete":  "celebrating",
    "silence":        "thinking",
    "game_start":     "happy",
    "stuck":          "encouraging",
}

@router.post("/avatar/respond", response_model=AvatarResponse)
async def avatar_respond(request: AvatarRequest):
    print(f" Request: event={request.event_type}, text='{request.voice_text}', child={request.child_name}")

    # Check if child wants to open a game (intent parsing)
    game_action: str | None = None
    if request.voice_text:
        intent = parse_intent(request.voice_text)
        print(f" Intent: {intent}")
        if intent["intent"] == "OPEN_GAME":
            game_action = intent["game_id"]

    ai_text, ai_text_ur = get_avatar_response(request)
    print(f" AI response: {ai_text}")

    # Pick expression
    expression = EXPRESSIONS.get(request.event_type, "neutral")
    print(f" AI Expression: {expression}")

    return AvatarResponse(
        avatar_response=ai_text,
        avatar_response_ur=ai_text_ur, 
        expression=expression,
        success=True,
        game_action=game_action,
    )

@router.get("/health")
def health_check():
    return {"status": "ok", "message": "Avatar backend is running!"}