# Maps spoken words (English, Roman Urdu, and Urdu Script) → game screen IDs
GAME_KEYWORDS: dict[str, str] = {
    # Everyday Basics
    "everyday":       "everyday_basics",
    "basics":         "everyday_basics",
    "daily":          "everyday_basics",
    "rozmara":        "everyday_basics",
    "bunyaadi":       "everyday_basics",
    "روزمرہ":          "everyday_basics",
    "بنیادی":         "everyday_basics",

    # Built Memory
    "memory":         "built_memory",
    "remember":       "built_memory",
    "memorize":       "built_memory",
    "yaad":           "built_memory",
    "hafza":          "built_memory",
    "یاد":            "built_memory",
    "حافظہ":          "built_memory",

    # I Can Sense
    "sense":          "i_can_sense",
    "senses":         "i_can_sense",
    "feel":           "i_can_sense",
    "touch":          "i_can_sense",
    "hiss":           "i_can_sense",
    "choona":         "i_can_sense",
    "mehsoos":        "i_can_sense",
    "حس":             "i_can_sense",
    "چھونا":          "i_can_sense",
    "محسوس":          "i_can_sense",

    # Numbers in Action
    "number":         "numbers_in_action",
    "numbers":        "numbers_in_action",
    "count":          "numbers_in_action",
    "counting":       "numbers_in_action",
    "math":           "numbers_in_action",
    "hisaab":         "numbers_in_action",
    "ginti":          "numbers_in_action",
    "adad":           "numbers_in_action",
    "کاؤنٹنگ":        "numbers_in_action",
    "گنتی":           "numbers_in_action",
    "حساب":           "numbers_in_action",
    "نمبر":           "numbers_in_action",

    # Communicate
    "talk":           "communicate",
    "speak":          "communicate",
    "communicate":    "communicate",
    "words":          "communicate",
    "baat":           "communicate",
    "bolna":          "communicate",
    "lafaz":          "communicate",
    "gufftago":       "communicate",
    "بات":            "communicate",
    "بولنا":          "communicate",
    "لفظ":            "communicate",
    "گفتگو":          "communicate",
    "communication":  "communicate",

    # Decision Making (module-level)
    "decision":       "decision_making",
    "choose":         "decision_making",
    "choice":         "decision_making",
    "pick":           "decision_making",
    "faisla":         "decision_making",
    "chuna":          "decision_making",
    "فیصلہ":          "decision_making",
    "چننا":           "decision_making",

    # Old shape/letter/color games (keep for backward compat)
    "shape":          "shape_matching",
    "shakal":         "shape_matching",
    "شکل":            "shape_matching",
    "letter":         "letter_recognition",
    "harf":           "letter_recognition",
    "huroof":         "letter_recognition",
    "حرف":            "letter_recognition",
    "حروف":           "letter_recognition",
    "color":          "color_game",
    "colour":         "color_game",
    "rang":           "color_game",
    "رنگ":            "color_game",
}

# ── Sub-module keywords ──────────────────────────────────────────────────────
SUB_MODULE_KEYWORDS: dict[str, list[str]] = {
    "hygiene": [
        "hygiene", "clean", "brush", "wash", "safai", "صفائی", "حفظان صحت",
        "برش", "ہائیجین", "saaf", "صاف", "dhona", "دھونا",
    ],
    "decision": [
        "decision game", "decision making game", "decision making story",
        "faisla game", "decision story", "فیصلہ گیم", "فیصلہ کہانی",
    ],
    "danger": [
        "danger", "khatra", "safe", "safety", "hifazat",
        "خطرے", "حفاظت", "ڈینجر", "خطرہ",
    ],
    "emotion": [
        "emotion", "feeling", "mood", "jazbaat",
        "جذبات", "احساس", "ایموشن",
    ],
    "social": [
        "social", "friend", "people", "milna", "interaction",
        "سماجی", "دوست", "ملنا", "social interaction",
    ],
    "daily": [
        "daily life", "home routine", "rozmara zindagi",
        "روزمرہ زندگی",
    ],
}

# Maps sub-module ID → parent module screen ID
SUB_MODULE_PARENT: dict[str, str] = {
    "hygiene":  "decision_making",
    "decision": "decision_making",
    "danger":   "danger_detection",
    "emotion":  "emotion_control",
    "social":   "social_interaction",
    "daily":    "everyday_basics",
}

STORY_SIGNALS = [
    "story", "kahani", "listen", "qissa", "sunao", "tell me", "suno",
    "کہانی", "قصہ", "سنو", "سنانا", "سناؤ",
]

GAME_SIGNALS = [
    "game", "play", "khel", "khelo", "start", "open", "kholo", "chalao",
    "shuru", "گیم", "کھیل", "کھیلنا", "اوپن",
]

HELP_SIGNALS = [
    "help", "don't know", "dont know", "stuck", "confused", "i give up",
    "madad", "samjh nahi", "mushkil", "مدد", "سمجھ نہیں", "مشکل",
]


def _find_sub_module(text: str) -> str | None:
    """Return the first sub-module key whose keyword list has a hit in text."""
    for sub, keywords in SUB_MODULE_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return sub
    return None


def parse_intent(voice_text: str) -> dict:
    if not voice_text:
        return {"intent": "GENERAL"}

    text = voice_text.lower().strip()

    is_story_request = any(s in text for s in STORY_SIGNALS)
    is_game_request  = any(g in text for g in GAME_SIGNALS)

    # ── 1. Sub-module match ──────────────────────────────────────────────────
    found_sub = _find_sub_module(text)

    if found_sub:
        parent = SUB_MODULE_PARENT.get(found_sub, "")

        if is_story_request:          # story wins — checked FIRST
            return {"intent": "OPEN_GAME", "game_id": f"{found_sub}_story", "parent": parent}
    
        elif is_game_request:
            return {"intent": "OPEN_GAME", "game_id": f"{found_sub}_game", "parent": parent}
        
        else:
            return {"intent": "OPEN_GAME", "game_id": parent if parent else found_sub, "parent": parent}

    # ── 2. Story with no specific category ──────────────────────────────────
    if is_story_request and not is_game_request:
        return {"intent": "SUGGEST_STORIES"}

    # ── 3. Broad module keyword + game signal ────────────────────────────────
    if is_game_request:
        for keyword, game_id in GAME_KEYWORDS.items():
            if keyword in text:
                return {"intent": "OPEN_GAME", "game_id": game_id}

    return {"intent": "GENERAL"}