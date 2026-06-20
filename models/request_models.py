from pydantic import BaseModel
from typing import Optional

class AvatarRequest(BaseModel):
    child_name:        str = "friend"
    avatar_name:       str = "Sunny"
    event_type:        str = "voice_command"
    voice_text:        Optional[str] = ""
    attempt_count:     int = 1
    game_id:           str = ""
    specific_target:   str = ""
    child_last_action: str = ""
    language:          str = "en"          # ← ADD THIS

class AvatarResponse(BaseModel):
    avatar_response:    str
    avatar_response_ur: Optional[str] = None  # ← ADD THIS
    expression:         str
    success:            bool
    game_action:        Optional[str] = None