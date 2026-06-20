"""
speech_service.py
==================
Pronunciation checking engine — ported from the old ai_module.py.

Pipeline:
    TTS  (ai_speak)  -> edge_tts generates audio for the word/sentence to say
    STT  (ai_check)  -> faster-whisper transcribes the child's recording,
                         then a rule-based scorer compares it to what was expected
    ai_result()      -> turns a numeric score into a pass/fail message

NOTE: the original version also had a "semantic safety net" using
sentence-transformers for single words. That's been removed on purpose —
it added ~1GB+ of model weights and a slow first load for a secondary
check; the rule-based SequenceMatcher scoring below already handles
single-word leniency (accent tolerance) on its own.
"""

import os
import re
import asyncio
import uuid
from difflib import SequenceMatcher

import edge_tts
from faster_whisper import WhisperModel

# =============================================
# SETTINGS
# =============================================
PASS_SCORE = 70
AUDIO_FOLDER = "audio_files"
RECORDINGS_FOLDER = "recordings"
WHISPER_SIZE = os.environ.get("WHISPER_MODEL_SIZE", "small")  # use "base" or "tiny" if Railway RAM is tight

VOICES = {
    "english": "en-US-AriaNeural",
    "urdu": "ur-PK-UzmaNeural",
    "en": "en-US-AriaNeural",
    "ur": "ur-PK-UzmaNeural",
}
WHISPER_LANG = {
    "english": "en",
    "urdu": "ur",
    "en": "en",
    "ur": "ur",
}

os.makedirs(AUDIO_FOLDER, exist_ok=True)
os.makedirs(RECORDINGS_FOLDER, exist_ok=True)

# Lazy-loaded so the app boots fast and only pays the Whisper load cost
# the first time /check is actually called.
_whisper_model = None


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        print("⏳ Loading Whisper model...")
        _whisper_model = WhisperModel(WHISPER_SIZE, device="cpu", compute_type="int8")
        print("✅ Whisper ready")
    return _whisper_model


# =============================================
# KNOWLEDGE BASE
# =============================================
OPPOSITE_PAIRS = [
    ('happy', 'sad'), ('خوش', 'اداس'), ('good', 'bad'), ('nice', 'wrong'),
    ('nicely', 'badly'), ('اچھا', 'برا'), ('yummy', 'bad'), ('مزیدار', 'گندا'),
    ('dog', 'cat'), ('کتا', 'بلی'), ('fish', 'bird'), ('مچھلی', 'پرندے'),
    ('cow', 'goat'), ('گائے', 'بکری'), ('fly', 'swim'), ('اڑ', 'تیر'),
    ('open', 'close'), ('کھولو', 'بند'), ('come', 'go'), ('آو', 'جاو'),
    ('sit', 'stand'), ('بیٹھ', 'کھڑے'), ('water', 'sky'), ('پانی', 'آسمان'),
    ('inside', 'outside'), ('اندر', 'باہر'), ('day', 'night'), ('دن', 'رات'),
    ('fast', 'slow'), ('تیز', 'آہستہ'), ('love', 'hate'), ('پیار', 'نفرت'),
]

VERB_GROUPS = [
    {'run', 'running', 'دوڑ', 'دوڑنا', 'دوڑتا', 'دوڑتی'},
    {'fly', 'flying', 'اڑ', 'اڑنا', 'اڑتا', 'اڑتی', 'اڑ سکتے', 'باک', 'دونس'},
    {'swim', 'swimming', 'تیر', 'تیرنا'},
    {'walk', 'walking', 'چل', 'چلنا'},
    {'eat', 'eating', 'کھا', 'کھانا'},
    {'drink', 'drinking', 'پی', 'پینا'},
    {'sleep', 'sleeping', 'سو', 'سونا'},
    {'play', 'playing', 'کھیل', 'کھیلنا'},
    {'fight', 'fighting', 'لڑ', 'لڑنا'},
    {'sit', 'sitting', 'بیٹھ', 'بیٹھنا'},
    {'stand', 'standing', 'کھڑے', 'کھڑا'},
    {'open', 'کھولو', 'کھول'},
    {'close', 'بند', 'بند کرو'},
    {'wash', 'دھوؤ', 'دھونا'},
    {'live', 'lives', 'رہتی', 'رہتا', 'رہنا'},
    {'make', 'makes', 'بناتی', 'بنانا'},
    {'miss', 'یاد', 'یاد آتی'},
    {'come', 'coming', 'آ', 'آنا'},
    {'comb', 'combing', 'کنگھی', 'کنگھی کرنا'},
    {'brush', 'brushing', 'برش', 'صاف کرنا'},
]

SUBJECT_GROUPS = [
    {'dog', 'کتا'}, {'cat', 'بلی'}, {'fish', 'مچھلی'}, {'bird', 'پرندے'}, {'cow', 'گائے'},
    {'goat', 'بکری'}, {'hen', 'مرغی'}, {'horse', 'گھوڑا'}, {'sheep', 'بھیڑ'}, {'lion', 'شیر'},
    {'sister', 'بہن'}, {'brother', 'بھائی'}, {'mother', 'ماں', 'امی'}, {'father', 'ابو', 'باپ'},
    {'grandma', 'دادی', 'نانی'}, {'grandpa', 'دادا', 'نانا'},
    {'eyes', 'آنکھ', 'آنکھیں'}, {'nose', 'ناک'}, {'ear', 'ears', 'کان'}, {'mouth', 'منہ'},
    {'hands', 'ہاتھ'}, {'head', 'سر'}, {'feet', 'پاؤں', 'پیر'}, {'teeth', 'دانت', 'دانتوں'},
    {'hair', 'بال', 'بالوں'}, {'face', 'چہرہ'}, {'fingers', 'انگلی', 'انگلیوں'},
    {'eraser', 'ربڑ'}, {'sharpener', 'شوپنر'}, {'pencil', 'پینسل'}, {'notebook', 'کاپی'},
    {'book', 'کتاب'}, {'shoes', 'جوتے'},
]

LOCATION_GROUPS = [
    {'water', 'پانی'}, {'sky', 'آسمان'}, {'land', 'زمین'}, {'jungle', 'جنگل'},
    {'home', 'house', 'گھر'}, {'school', 'سکول', 'اسکول'}, {'dark', 'اندھیرا'}, {'light', 'روشنی'},
    {'desk', 'table', 'میز'}, {'floor', 'زمین', 'فرش'}, {'chair', 'کرسی'},
    {'toilet', 'washroom', 'bathroom', 'واش روم', 'ٹوائلٹ'},
]

STOP_WORDS_EN = {
    'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
    'my', 'your', 'his', 'its', 'our', 'their', 'is', 'am', 'are', 'was', 'were',
    'be', 'been', 'a', 'an', 'the', 'to', 'of', 'for', 'with', 'by', 'at', 'on', 'in',
    'do', 'does', 'did', 'have', 'has', 'had', 'will', 'would', 'could', 'should',
    'may', 'might', 'must', 'and', 'or', 'but', 'so', 'because', 'if', 'then'
}
STOP_WORDS_UR = {
    'میں', 'کو', 'سے', 'پر', 'کا', 'کی', 'کے', 'ہے', 'ہیں', 'ایک', 'یہ', 'وہ',
    'تم', 'آپ', 'ہم', 'ان', 'اس', 'نظر', 'رہا', 'رہی', 'رہے', 'سکتے', 'سکتی',
    'سکتا', 'آج', 'کیوں', 'ہو', 'ہوں', 'آتی', 'آتا', 'مجھے', 'اپنی', 'اپنے', 'اپنا'
}

NEG_WORDS = {'not', "don't", "doesn't", "isn't", "wasn't", "won't", "can't",
             'never', 'no', 'نہیں', 'نہ', 'مت'}

PRONOUN_PAIRS = [
    ('i', 'you'), ('you', 'i'),
    ('my', 'your'), ('your', 'my'),
    ('he', 'she'), ('she', 'he'),
    ('his', 'her'), ('her', 'his'),
    ('we', 'they'), ('they', 'we'),
    ('our', 'their'), ('their', 'our'),
]

WHISPER_FIXES = {
    "go": "cow", "ko": "cow", "kow": "cow", "got": "goat", "god": "goat", "gote": "goat",
    "kat": "cat", "cot": "cat", "dok": "dog", "doc": "dog", "dawg": "dog",
    "fis": "fish", "wish": "fish", "burd": "bird", "berd": "bird", "han": "hen",
}
UR_WHISPER_FIXES = {'ڈانس': 'اداس', 'دونس': 'اڑ', 'باک': 'اڑ'}


# =============================================
# TTS
# =============================================
async def ai_speak(input_data, language="english", speed="slow") -> dict:
    try:
        text = _extract_text(input_data)
        lang = language.lower().strip()
        voice = VOICES.get(lang, VOICES["english"])
        if not text:
            return {"success": False, "error_code": "NO_TEXT", "message": "No text", "text": ""}

        safe_name = re.sub(r"[^a-zA-Z0-9\u0600-\u06FF]", "_", text.strip())[:50]
        suffix = f"_{speed}" if speed != "slow" else ""
        path = os.path.join(AUDIO_FOLDER, f"{lang}_{safe_name}{suffix}.mp3")

        if not os.path.exists(path):
            print(f"🔊 Generating TTS: '{text}' [{lang}] speed {speed}")
            rate = {'slow': '-25%', 'normal': '0%', 'fast': '+15%'}.get(speed, '-25%')
            for _ in range(3):
                try:
                    tts = edge_tts.Communicate(text, voice=voice, rate=rate)
                    await tts.save(path)
                    break
                except Exception as e:
                    print(f"⚠️ TTS attempt failed: {e}")
                    await asyncio.sleep(1)
            else:
                return {"success": False, "error_code": "TTS_FAILED", "message": "Audio not generated", "text": text}
            print(f"✅ Audio saved: {path}")

        return {"success": True, "audio_path": path, "text": text, "language": lang, "speed": speed}
    except Exception as e:
        return {"success": False, "error_code": "TTS_FAILED", "message": str(e), "text": str(input_data)}


# =============================================
# STT + SCORE
# =============================================
def ai_check(audio_path: str, expected_input, language: str = "english") -> dict:
    try:
        expected = _extract_text(expected_input)
        lang = language.lower().strip()
        whisper_lang = WHISPER_LANG.get(lang, "en")

        if not expected:
            return {"success": False, "error_code": "NO_EXPECTED", "score": 0, "correct": False}
        if not os.path.exists(audio_path):
            return {"success": False, "error_code": "FILE_NOT_FOUND", "score": 0, "correct": False}

        print(f"🎤 Processing: {audio_path} [{lang}]")
        print(f"📝 Expected: '{expected}'")

        model = _get_whisper_model()
        segments, _ = model.transcribe(
            audio_path, beam_size=5, language=whisper_lang,
            initial_prompt=f"The child is saying: {expected}", temperature=0.0,
            vad_filter=True,
            vad_parameters={"threshold": 0.3, "min_speech_duration_ms": 100, "min_silence_duration_ms": 500}
        )
        heard = " ".join([s.text.strip() for s in segments])
        print(f"🔍 RAW: '{heard}'")

        heard = _fix_hallucination(heard)
        heard = _fix_whisper_output(heard, expected)
        print(f"👂 Cleaned: '{heard}'")

        score = _smart_score(expected, heard, lang)
        print(f"📊 Score: {round(score)}%")

        return {
            "success": True, "expected": expected, "heard": heard,
            "score": round(score), "correct": score >= PASS_SCORE,
            "pass_score": PASS_SCORE, "language": lang
        }
    except Exception as e:
        print(f"❌ STT Error: {e}")
        return {"success": False, "error_code": "STT_FAILED", "message": str(e), "score": 0, "correct": False}


def ai_result(score) -> dict:
    if score >= PASS_SCORE:
        return {"status": "correct", "message": "Good Job! 🌟", "score": score, "next": True}
    return {"status": "repeat", "message": "Try Again! 🔄", "score": score, "next": False}


def get_recording_path() -> str:
    return os.path.join(RECORDINGS_FOLDER, f"{str(uuid.uuid4())[:8]}.wav")


# =============================================
# HELPERS
# =============================================
def _extract_text(inp) -> str:
    if isinstance(inp, str):
        return inp.strip()
    if isinstance(inp, dict):
        for k in ["text", "word", "sentence", "content", "data"]:
            if k in inp:
                return str(inp[k]).strip()
    return str(inp).strip()


def _fix_hallucination(t: str) -> str:
    if not t or len(t) < 20:
        return t
    words = t.split()
    if len(words) > 50:
        print(f"🛑 Trimming long text ({len(words)} words)")
        return " ".join(words[:15])
    for i in range(len(words) - 4):
        phrase = tuple(words[i:i + 4])
        if sum(1 for j in range(len(words) - 3) if tuple(words[j:j + 4]) == phrase) >= 3:
            return " ".join(words[:i + 4])
    return t


def _fix_whisper_output(heard: str, expected: str) -> str:
    heard = re.sub(r'[^\w\s\u0600-\u06FF]', '', heard).strip()
    low = heard.lower().strip()

    if low in WHISPER_FIXES:
        fixed = WHISPER_FIXES[low]
        print(f"🔧 Whisper fix: '{heard}' → '{fixed}'")
        return fixed

    words = heard.split()
    changed = False
    new = []
    for w in words:
        if w in UR_WHISPER_FIXES and UR_WHISPER_FIXES[w] in expected:
            new.append(UR_WHISPER_FIXES[w])
            changed = True
        else:
            new.append(w)
    return " ".join(new) if changed else heard


def _get_group(w: str, groups: list) -> int:
    wl = w.lower()
    for i, g in enumerate(groups):
        if wl in g:
            return i
    return -1


def _get_key_words(text: str, lang: str) -> list:
    stop = STOP_WORDS_UR if lang in ('ur', 'urdu') else STOP_WORDS_EN
    return [w for w in text.split() if w not in stop and len(w) > 1]


def _has_pronoun_mismatch(expected: str, heard: str) -> bool:
    exp_lower = expected.lower()
    heard_lower = heard.lower()
    for p1, p2 in PRONOUN_PAIRS:
        if p1 in exp_lower and p2 in heard_lower and p1 not in heard_lower and p2 not in exp_lower:
            return True
    return False


# =============================================
# RULE-BASED SCORE
# =============================================
def _rule_based_score(expected: str, heard: str, lang: str) -> float:
    if not heard:
        return 0.0
    if expected == heard:
        return 100.0

    exp_l = expected.lower().strip()
    hrd_l = heard.lower().strip()

    def has_neg(t):
        return any(n in t for n in NEG_WORDS)
    if has_neg(exp_l) != has_neg(hrd_l):
        return 35.0

    for w1, w2 in OPPOSITE_PAIRS:
        if w1 in exp_l and w2 in hrd_l and w1 not in hrd_l:
            return 25.0
        if w2 in exp_l and w1 in hrd_l and w2 not in hrd_l:
            return 25.0

    exp_s = next((_get_group(w, SUBJECT_GROUPS) for w in exp_l.split() if _get_group(w, SUBJECT_GROUPS) >= 0), -1)
    hrd_s = next((_get_group(w, SUBJECT_GROUPS) for w in hrd_l.split() if _get_group(w, SUBJECT_GROUPS) >= 0), -1)
    if exp_s >= 0 and hrd_s >= 0 and exp_s != hrd_s:
        return 35.0

    exp_v = next((_get_group(w, VERB_GROUPS) for w in exp_l.split() if _get_group(w, VERB_GROUPS) >= 0), -1)
    hrd_v = next((_get_group(w, VERB_GROUPS) for w in hrd_l.split() if _get_group(w, VERB_GROUPS) >= 0), -1)
    if exp_v >= 0 and hrd_v >= 0 and exp_v != hrd_v:
        return 40.0

    exp_loc = next((_get_group(w, LOCATION_GROUPS) for w in exp_l.split() if _get_group(w, LOCATION_GROUPS) >= 0), -1)
    hrd_loc = next((_get_group(w, LOCATION_GROUPS) for w in hrd_l.split() if _get_group(w, LOCATION_GROUPS) >= 0), -1)
    if exp_loc >= 0 and hrd_loc >= 0 and exp_loc != hrd_loc:
        return 35.0

    exp_kw = _get_key_words(exp_l, lang)
    hrd_kw = _get_key_words(hrd_l, lang)
    if not exp_kw:
        return 80.0

    if len(exp_kw) == 1 and len(hrd_kw) == 1:
        r = SequenceMatcher(None, exp_kw[0], hrd_kw[0]).ratio()
        if r >= 0.85:
            return 100.0
        if r >= 0.70:
            return 85.0
        if r >= 0.55:
            return 70.0
        return max(5.0, r * 60)

    matched = 0.0
    for ew in exp_kw:
        best = max((SequenceMatcher(None, ew, hw).ratio() for hw in hrd_kw), default=0.0)
        if len(ew) <= 5 and best >= 0.6:
            best = min(1.0, best + 0.15)
        if best >= 0.80:
            matched += 1.0
        elif best >= 0.65:
            matched += 0.65
        elif best >= 0.50:
            matched += 0.35
    word_sc = (matched / len(exp_kw)) * 100
    len_ratio = len(hrd_kw) / max(len(exp_kw), 1)
    effort = 12 if len_ratio >= 0.8 else (8 if len_ratio >= 0.6 else (5 if len_ratio >= 0.4 else 0))
    return min(98.0, word_sc + effort)


# =============================================
# MAIN SMART SCORE
# =============================================
def _smart_score(expected: str, heard: str, lang: str = "en") -> float:
    if not heard or not heard.strip():
        return 0.0
    if expected == heard:
        return 100.0

    exp_lower = expected.lower().strip()
    heard_lower = heard.lower().strip()
    exp_words = exp_lower.split()
    heard_words = heard_lower.split()

    # ----- SENTENCE (>= 2 words): strict core-meaning check -----
    if len(exp_words) > 1:
        if _has_pronoun_mismatch(expected, heard):
            print("⚠️ Pronoun mismatch (e.g., your/my, he/she)")
            return 30.0

        exp_neg = any(n in exp_lower for n in NEG_WORDS)
        heard_neg = any(n in heard_lower for n in NEG_WORDS)
        if exp_neg != heard_neg:
            print("⚠️ Negation mismatch in sentence")
            return 35.0

        if len(heard_words) < len(exp_words) * 0.7:
            print(f"⚠️ Too short sentence: {heard_words}")
            return 30.0

        stop = STOP_WORDS_UR if lang in ('ur', 'urdu') else STOP_WORDS_EN
        exp_keys = [w for w in exp_lower.split() if w not in stop and len(w) > 1]
        heard_keys = [w for w in heard_lower.split() if w not in stop and len(w) > 1]
        if not exp_keys:
            return _rule_based_score(expected, heard, lang)

        matched = 0
        for ek in exp_keys:
            best = max((SequenceMatcher(None, ek, hk).ratio() for hk in heard_keys), default=0.0)
            if best >= 0.85:
                matched += 1
            elif best >= 0.70 and len(ek) <= 5 and ek in ['cow', 'goat', 'fish', 'cat', 'dog', 'hen', 'bird']:
                matched += 0.8
            else:
                print(f"❌ Key word mismatch: '{ek}' not found (best={best:.2f})")
                return 30.0

        key_ratio = matched / len(exp_keys) if exp_keys else 1.0
        if key_ratio < 0.9:
            print(f"⚠️ Only {key_ratio:.0%} of key words matched")
            return 35.0

        rule_score = _rule_based_score(expected, heard, lang)
        return min(95.0, max(75.0, rule_score))

    # ----- SINGLE WORD: lenient rule-based score -----
    return _rule_based_score(expected, heard, lang)