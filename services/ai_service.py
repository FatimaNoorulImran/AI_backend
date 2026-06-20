import os
from groq import Groq
from dotenv import load_dotenv
from services.prompt_builder import build_system_prompt, build_context
from models.request_models import AvatarRequest

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# ── English Basic Q&A ─────────────────────────────────────────────────────────
BASIC_QA_EN = {
    ("your name", "who are you"):        lambda n, a: f"My name is {a}! I am your learning buddy!",
    ("how are you", "how do you feel"):  lambda n, a: f"I am super happy to be here with you {n}!",
    ("hello", "hi", "hey"):              lambda n, a: f"Hello {n}! What shall we do today?",
    ("bye", "goodbye", "see you"):       lambda n, a: f"Goodbye {n}! Come back soon, I will miss you!",
    ("thank you", "thanks"):             lambda n, a: f"You are so welcome {n}! You are amazing!",
    ("love you", "i love you"):          lambda n, a: f"I love you too {n}! You are my favourite friend!",
    ("what can you do", "help me"):      lambda n, a: f"I can play games with you and answer your questions {n}!",
}

GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
]

# ── Story suggestion (no specific category) ───────────────────────────────────
STORY_SUGGESTIONS = {
    "en": (
        "I love stories! I have stories about Safety, Emotions, Social skills, "
        "Hygiene, and Daily Life. Which one would you like to hear?",
        "مجھے کہانیاں بہت پسند ہیں! میرے پاس خطرے، جذبات، سماجی مہارت، "
        "صفائی اور روزمرہ زندگی کی کہانیاں ہیں۔ کون سی سننا چاہیں گے؟",
    ),
    "ur": (
        "مجھے کہانیاں بہت پسند ہیں! میرے پاس خطرے کی پہچان، جذبات، سماجی "
        "مہارت، صفائی اور روزمرہ زندگی کی کہانیاں ہیں۔ کون سی سننا چاہیں گے؟",
        None,
    ),
}

# ── Canned responses for each game/story ID ───────────────────────────────────
GAME_OPEN_MSGS: dict[str, dict] = {
    # Hygiene
    "hygiene_game": {
        "en": ("Yay! Let us learn about keeping clean! Opening Hygiene game!",
               "واہ! آئیں صفائی کے بارے میں سیکھیں! صفائی کا گیم شروع ہو رہا ہے!"),
        "ur": ("واہ! آئیں صفائی کے بارے میں سیکھیں! صفائی کا گیم شروع ہو رہا ہے!", None),
    },
    "hygiene_story": {
        "en": ("Let us read a Hygiene story together! Opening stories now!",
               "آئیں صفائی کی کہانی پڑھتے ہیں!"),
        "ur": ("آئیں صفائی کی کہانی پڑھتے ہیں!", None),
    },
    # Danger
    "danger_game": {
        "en": ("Let us learn how to stay safe! Opening Safety game!",
               "آئیں محفوظ رہنا سیکھیں! حفاظت کا گیم شروع ہو رہا ہے!"),
        "ur": ("آئیں محفوظ رہنا سیکھیں! حفاظت کا گیم شروع ہو رہا ہے!", None),
    },
    "danger_story": {
        "en": ("Story time! Let us learn about staying safe!",
               "کہانی کا وقت! آئیں محفوظ رہنا سیکھیں!"),
        "ur": ("کہانی کا وقت! آئیں محفوظ رہنا سیکھیں!", None),
    },
    # Emotion
    "emotion_game": {
        "en": ("Feelings are so important! Opening Emotions game!",
               "جذبات بہت اہم ہیں! جذبات کا گیم شروع ہو رہا ہے!"),
        "ur": ("جذبات بہت اہم ہیں! جذبات کا گیم شروع ہو رہا ہے!", None),
    },
    "emotion_story": {
        "en": ("Let us read a feelings story together!",
               "آئیں جذبات کی کہانی پڑھتے ہیں!"),
        "ur": ("آئیں جذبات کی کہانی پڑھتے ہیں!", None),
    },
    # Social
    "social_game": {
        "en": ("Making friends is so fun! Opening Social skills game!",
               "دوست بنانا بہت مزیدار ہے! سماجی گیم شروع ہو رہا ہے!"),
        "ur": ("دوست بنانا بہت مزیدار ہے! سماجی گیم شروع ہو رہا ہے!", None),
    },
    "social_story": {
        "en": ("Story time! Let us learn about making friends!",
               "آئیں دوستی کی کہانی پڑھتے ہیں!"),
        "ur": ("آئیں دوستی کی کہانی پڑھتے ہیں!", None),
    },
    # Decision
    "decision_game": {
        "en": ("Let us practice making great choices! Opening Decision Making game!",
               "آئیں اچھے فیصلے کرنا سیکھیں! فیصلہ گیم شروع ہو رہا ہے!"),
        "ur": ("آئیں اچھے فیصلے کرنا سیکھیں! فیصلہ گیم شروع ہو رہا ہے!", None),
    },
    "decision_story": {
        "en": ("Let us read a Decision Making story together!",
               "آئیں فیصلہ کی کہانی پڑھتے ہیں!"),
        "ur": ("آئیں فیصلہ کی کہانی پڑھتے ہیں!", None),
    },
    # Module homes
    "decision_making": {
        "en": ("Let us explore Decision Making together!",
               "آئیں فیصلہ سازی کو ایک ساتھ دیکھیں!"),
        "ur": ("آئیں فیصلہ سازی کو ایک ساتھ دیکھیں!", None),
    },
    "danger_detection": {
        "en": ("Let us learn about staying safe!",
               "آئیں محفوظ رہنا سیکھیں!"),
        "ur": ("آئیں محفوظ رہنا سیکھیں!", None),
    },
    "emotion_control": {
        "en": ("Let us explore our feelings together!",
               "آئیں اپنے جذبات کو سمجھیں!"),
        "ur": ("آئیں اپنے جذبات کو سمجھیں!", None),
    },
    "social_interaction": {
        "en": ("Let us learn about making friends!",
               "آئیں دوستی کے بارے میں سیکھیں!"),
        "ur": ("آئیں دوستی کے بارے میں سیکھیں!", None),
    },
}


def _check_basic_qa(
    voice_text: str, child_name: str, avatar_name: str, language: str = "en"
) -> str | None:
    text_lower = voice_text.strip().lower()
    words = text_lower.split()
    name  = child_name  if child_name  else "friend"
    buddy = avatar_name if avatar_name else "Sunny"

    for keywords, reply_fn in BASIC_QA_EN.items():
        for kw in keywords:
            if " " in kw and kw in text_lower:
                return reply_fn(name, buddy)
            elif kw in words:
                return reply_fn(name, buddy)
    return None


def _translate_to_urdu(english_text: str) -> str | None:
    for model in GROQ_MODELS:
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Translate the following to simple Urdu for a child. "
                            "You MUST write in Urdu script (Arabic letters) only. "
                            "Do NOT use Roman Urdu or English letters. "
                            "Example output: آپ بہت اچھے ہیں! "
                            "Reply with ONLY the Urdu script translation, nothing else."
                        ),
                    },
                    {"role": "user", "content": english_text},
                ],
                temperature=0.3,
                max_tokens=100,
            )
            urdu = completion.choices[0].message.content.strip()
            print(f"  Urdu translation [{model}]: {urdu}")
            return urdu
        except Exception as e:
            print(f"  Translation failed on {model}: {e}")
            continue
    return None


def get_avatar_response(request: AvatarRequest) -> tuple[str, str | None]:
    from services.intent_parser import parse_intent

    intent = parse_intent(request.voice_text)
    lang   = request.language

    print(f"  Intent resolved: {intent}")

    # ── Story suggestion (no specific category) ───────────────────────────────
    if intent["intent"] == "SUGGEST_STORIES":
        en_text, ur_text = STORY_SUGGESTIONS.get(lang, STORY_SUGGESTIONS["en"])
        if lang == "ur":
            return (en_text, None)
        return (en_text, ur_text)

    # ── Game / story / module opening ─────────────────────────────────────────
    if intent["intent"] == "OPEN_GAME":
        game_id = intent.get("game_id", "")
        if game_id in GAME_OPEN_MSGS:
            en_text, ur_text = GAME_OPEN_MSGS[game_id].get(
                lang, GAME_OPEN_MSGS[game_id]["en"]
            )
            if lang == "ur":
                return (en_text, None)
            return (en_text, ur_text)
        # Generic fallback
        label = game_id.replace("_", " ")
        if lang == "ur":
            return (f"واہ! {label} شروع ہو رہا ہے!", None)
        return (f"Yay! Let us open the {label}!", f"واہ! {label} شروع ہو رہا ہے!")

    # ── Basic Q&A fast path ───────────────────────────────────────────────────
    if request.voice_text:
        quick = _check_basic_qa(
            request.voice_text, request.child_name,
            request.avatar_name, request.language
        )
        if quick:
            if lang == "ur":
                return (quick, None)
            return (quick, _translate_to_urdu(quick))

    # ── Groq AI call ──────────────────────────────────────────────────────────
    try:
        system = build_system_prompt(request.child_name, request.avatar_name)
    except Exception as e:
        print(f"  Prompt build error: {e}")
        system = (
            f"You are a friendly helper named {request.avatar_name} "
            f"for a child named {request.child_name}. "
            "Be warm, simple, and encouraging. Always answer questions directly."
        )

    context = build_context(
        request.event_type,
        request.game_id,
        request.attempt_count,
        request.specific_target,
        request.child_last_action,
        request.voice_text,
        request.language,
    )

    for model in GROQ_MODELS:
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": context},
                ],
                temperature=0.7,
                max_tokens=150,
            )
            text = completion.choices[0].message.content.strip()
            print(f"  Groq [{model}] replied: {text[:100]}...")
            if lang == "ur":
                return (text, None)
            return (text, _translate_to_urdu(text))
        except Exception as e:
            print(f"  Model {model} failed: {e}")
            continue

    # ── Local fallback ────────────────────────────────────────────────────────
    if lang == "ur":
        return ("آپ بہت اچھا کر رہے ہیں! جاری رکھیں!", None)
    fallback_en = "You are doing amazing! Let us keep going!"
    return (fallback_en, _translate_to_urdu(fallback_en))