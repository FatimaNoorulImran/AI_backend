import os

def build_system_prompt(child_name: str, avatar_name: str) -> str:
    path = os.path.join(os.path.dirname(__file__), "../prompts/system_prompt.txt")
    with open(path, "r", encoding="utf-8") as f:
        template = f.read()
    return template.replace("{child_name}", child_name).replace("{avatar_name}", avatar_name)


def build_context(event_type, game_id, attempt_count,
                  specific_target, child_last_action, voice_text,
                  language="en") -> str:

    from services.intent_parser import parse_intent
    intent = parse_intent(voice_text)
    
    situational_note = ""
    if intent["intent"] == "OPEN_GAME":
        situational_note = f"ACTION: The child wants to start the {intent['game_id']} module! Be extremely excited and invite them to play with you."

    return f"""
{situational_note}

CURRENT SITUATION:
- Event: {event_type}
- Game: {game_id}
- Attempt number: {attempt_count}
- Task for child: {specific_target}
- What child did: {child_last_action}
- What child said: "{voice_text}"

REMEMBER:
- If the child asked a question, ANSWER IT DIRECTLY.
- Only use encouragement phrases (کوشش کرو / Try again) for GAME WRONG ANSWERS.
- Never give generic encouragement when a question is asked.
"""