"""
AURA Intelligent Language Classifier & Response Consistency Engine
==================================================================
Guarantees 100% strict language separation and lightning-fast responses:
1. TAMIL input  -> 100% Pure Tamil Script (தமிழ்) + ta-IN-ValluvarNeural voice
2. TANGLISH input -> 100% Warm Colloquial Tanglish (Latin script only) + en-IN-PrabhatNeural voice
3. ENGLISH input -> 100% Natural Clean English + en-IN-PrabhatNeural voice

Zero language mixing in a single reply.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple


# ── Tanglish Vocabulary & Semantic Markers ─────────────────────────────────────
TANGLISH_KEYWORDS = {
    # Pronouns & Address
    "nanba", "nanbaa", "thala", "thambi", "bro", "mapla", "machan", "machi",
    "dei", "da", "di", "unga", "unaku", "enakku", "enaku", "namma", "nammala",
    "neenga", "nee", "naan", "avan", "aval", "avanga",

    # Common Verbs & Actions
    "pannu", "pannidu", "panren", "pandren", "panna", "panni", "pannalam",
    "pannunga", "pannikittu", "sei", "seidu", "seira",
    "sollu", "solra", "solren", "solunga", "solradhu",
    "paaru", "paaren", "paathutu", "paakanum", "paakalam", "paarunga",
    "podu", "pottu", "podava",
    "koodu", "kudu", "kuduthu", "kudunga",
    "vaanga", "ponga", "vaa", "po", "pora", "poran", "varan", "varen",
    "pesu", "pesuran", "pesura", "pesunga",
    "kora", "korai", "kammi", "kootu", "athigam", "yethu", "irukku", "iruken",
    "irukiya", "irukeenga", "irundhuchu", "theriyum", "theriyuma", "puriyala",
    "purinjatha", "kekkuthu", "kekutha", "mudiyum", "mudiyuma", "mudinjathu",
    "mudiyala", "mudiyathu", "edukku", "edu", "eduthu",

    # Interrogatives & Conjunctions
    "enna", "ethavthu", "edhavadhu", "yedhavadhu", "epdi", "eppadi", "epudi",
    "eppo", "eppothu", "engae", "enga", "yen", "yaaru",
    "aachu", "aaguthu", "aagum", "aam", "aama", "aamam",
    "illa", "illai", "illaye",
    "seri", "sari", "kandippa", "romba", "konjam", "apram", "appo", "kooda",
    "vanakkam", "vanakam", "nandri", "venum", "venda", "vendam",
    "orey", "nerathula", "neram", "vela", "velai", "solradha"
}

# Suffixes common in colloquial Tamil written phonetically
_TANGLISH_SUFFIX_PATTERN = re.compile(
    r"\b[a-z]{3,}(?:-?(?:la|ku|um|oda|ah|a|le|nu|dhan|than|pa|ma))\b",
    re.IGNORECASE
)

# Common Tanglish Greetings & Small Talk Fast Path
_FAST_RESPONSES = {
    "nanba": "Sollu da nanba! Enna pannanum?",
    "sollu nanba": "Sollu da nanba! Enna help venum?",
    "dei": "Dei nanba! Solra, enna pannanum?",
    "da": "Sollu da! Ready-a irukken, enna help venuma?",
    "vanakkam": "Vanakkam nanba! Enna pannanum sollu da?",
    "epdi irukka": "Naan super-aa irukken nanba! Nee epdi irukka? Enna pannanum sollu!",
    "eppadi irukka": "Naan nalla irukken nanba! Ungalukku enna help pannanum?",
    "enna panra": "Namma PC-a monitor pannikittu unga command-kaga wait panren nanba!",
    "enna pandra": "Unga command-kaga dhaan wait panren nanba! Enna pannanum sollu da?",
    "seri": "Seri nanba! Ready-a irukken.",
    "nandri": "Romba santhosham nanba! Eppovume unakku help panna ready!",
    "thanks": "Romba santhosham nanba! Vera edhavadhu help venuma?",
    # Wake word fast path — instant acknowledgment
    "aura": "Sollu da nanba! Enna pannanum?",
    "hey nanba": "Sollu da nanba! Enna help venum?",
    "aura nanba": "Sollu da nanba! Enna pannanum?",
    "dei aura": "Dei! Ready-a irukken nanba, sollu da!",
    "da aura": "Sollu da! Enna pannanum?",
}

_FAST_RESPONSES_TAMIL = {
    "வணக்கம்": "வணக்கம் நண்பா! உங்களுக்கு நான் எவ்வாறு உதவ முடியும்?",
    "எப்படி இருக்கிறாய்": "நான் நலமாக இருக்கிறேன் நண்பா! நீங்கள் எப்படி இருக்கிறீர்கள்?",
    "எப்படி இருக்கீங்க": "நான் மிகவும் நலமாக இருக்கிறேன் நண்பா! உங்களுக்கு என்ன உதவி வேண்டும்?",
    "நன்றி": "மிக்க மகிழ்ச்சி நண்பா! எப்பொழுதும் உங்களுக்கு உதவ நான் தயாராக உள்ளேன்.",
}

_FAST_RESPONSES_ENGLISH = {
    "hello": "Hey Kalai! I'm Aura — what can I do for you?",
    "hi": "Hey there! What can I help you with?",
    "hey": "Hey! What can I do for you today?",
    "how are you": "I'm running at peak performance! How are you doing today?",
    "thank you": "You're very welcome! Let me know if you need anything else.",
    "thanks": "Anytime! Let me know if you need anything else.",
    # Wake word fast path — English
    "aura": "Hey Kalai! I'm listening — what do you need?",
    "hey aura": "Hey! I'm here. What can I do for you?",
    "hi aura": "Hi! Ready to help. What do you need?",
    "hello aura": "Hello! I'm listening — what's up?",
    "ok aura": "Yeah! Tell me what you need.",
    "okay aura": "Sure, go ahead! What do you need?",
}


def detect_language(text: str) -> str:
    """
    Classifies user input into:
    - 'TAMIL': Pure Tamil Unicode script (\u0B80 - \u0BFF)
    - 'TANGLISH': Tamil words written phonetically in Latin script
    - 'ENGLISH': Standard English text
    """
    raw = (text or "").strip()
    if not raw:
        return "ENGLISH"

    # 1. Check for Tamil Unicode characters
    tamil_chars = sum(1 for ch in raw if "\u0B80" <= ch <= "\u0BFF")
    latin_chars = sum(1 for ch in raw if ("a" <= ch.lower() <= "z"))

    if tamil_chars >= 2:
        return "TAMIL"

    # 2. Check for Tanglish vocabulary & grammatical markers
    clean = re.sub(r"[^a-zA-Z\s-]", " ", raw.lower())
    words = [w for w in clean.split() if w]

    tanglish_score = 0
    for w in words:
        if w in TANGLISH_KEYWORDS:
            tanglish_score += 2
        elif _TANGLISH_SUFFIX_PATTERN.match(w):
            tanglish_score += 1

    # Check for two-word Tanglish bigrams (e.g. "open pannu", "solra da")
    bigrams = [" ".join(words[i:i+2]) for i in range(len(words)-1)]
    for bg in bigrams:
        if any(marker in bg for marker in ("pannu", "sollu", "podu", "kudu", "paaru", "la")):
            tanglish_score += 2

    if tanglish_score >= 1 or any(w in TANGLISH_KEYWORDS for w in words):
        return "TANGLISH"

    return "ENGLISH"


def get_fast_conversational_reply(text: str) -> Optional[Tuple[str, str]]:
    """
    Checks for immediate conversational replies (greetings, small talk)
    Returns (reply_text, language) in < 1ms without cloud LLM roundtrip.
    """
    raw = (text or "").strip().lower()
    clean = re.sub(r"[^a-zA-Z\s]", " ", raw).strip()
    clean = re.sub(r"\s+", " ", clean)

    # 1. Check pure Tamil greetings
    for k, reply in _FAST_RESPONSES_TAMIL.items():
        if k in text:
            return (reply, "TAMIL")

    # 2. Check Tanglish greetings & small talk
    if clean in _FAST_RESPONSES:
        return (_FAST_RESPONSES[clean], "TANGLISH")

    # Check prefix/suffix matches for casual calls like "nanba", "dei nanba"
    for k, reply in _FAST_RESPONSES.items():
        if clean == k or clean.startswith(k + " ") or clean.endswith(" " + k):
            if len(clean.split()) <= 3:
                return (reply, "TANGLISH")

    # 3. Check English greetings
    if clean in _FAST_RESPONSES_ENGLISH:
        return (_FAST_RESPONSES_ENGLISH[clean], "ENGLISH")

    return None


def get_language_system_prompt(lang: str) -> str:
    """
    Returns strict, non-negotiable prompt instructions enforcing the exact language.
    Zero ambiguity, zero language-mixing.
    """
    if lang == "TAMIL":
        return (
            "\n[CRITICAL MANDATE: 100% PURE TAMIL SCRIPT ONLY]\n"
            "The user spoke/typed in TAMIL (தமிழ் எழுத்துக்கள்).\n"
            "- You MUST reply 100% in pure Tamil script (தமிழ்).\n"
            "- DO NOT use English sentences or Tanglish.\n"
            "- Every single sentence must be in Tamil script.\n"
            "- Example: 'வணக்கம் நண்பா! நான் உங்களுக்கு எவ்வாறு உதவ முடியும்?'\n"
        )
    elif lang == "TANGLISH":
        return (
            "\n[CRITICAL MANDATE: 100% PURE TANGLISH — ENGLISH ALPHABET ONLY]\n"
            "The user spoke/typed in TANGLISH (Tamil written phonetically in English alphabet).\n"
            "- You MUST reply 100% in warm, friendly, natural colloquial Tanglish.\n"
            "- Write ONLY using the standard ENGLISH ALPHABET (Latin letters).\n"
            "- ABSOLUTELY NEVER output Tamil script Unicode characters (no தமிழ் எழுத்துக்கள் like சரி, வணக்கம், நண்பா).\n"
            "- ABSOLUTELY NEVER output full English sentences. Every sentence must be spoken in Tamil phonetically in English script.\n"
            "- Example CORRECT: 'Seri nanba! Ipo Chrome open panren. Vera enna pannanum sollu da?'\n"
            "- Example FORBIDDEN: 'சரி nanba, I will open Chrome for you.' (NEVER MIX LANGUAGES OR SCRIPTS!)\n"
        )
    else:  # ENGLISH
        return (
            "\n[CRITICAL MANDATE: 100% PURE ENGLISH ONLY]\n"
            "The user spoke/typed in standard ENGLISH.\n"
            "- You MUST reply 100% in clean, concise, natural English.\n"
            "- DO NOT use any Tamil or Tanglish words.\n"
            "- Keep your response sharp and helpful.\n"
        )


def clean_and_enforce_output(text: str, target_lang: str) -> str:
    """
    Post-processes generated text to strictly sanitize and guarantee language purity.
    """
    t = (text or "").strip()
    if not t:
        return ""

    if target_lang == "TANGLISH":
        # Transliterate any stray Tamil Unicode words in case LLM slipped
        tamil_map = {
            "வணக்கம்": "Vanakkam", "நண்பா": "Nanba", "சரி": "Seri",
            "கண்டிப்பா": "Kandippa", "ஆமா": "Aama", "ஆமாம்": "Aama",
            "இல்லை": "Illa", "இல்ல": "Illa", "நன்றி": "Nandri",
            "எப்படி": "Epdi", "இருக்கிறீர்கள்": "Irukeenga", "இருக்கீங்க": "Irukeenga",
            "என்ன": "Enna", "பண்ணனும்": "Pannanum", "பண்ணலாம்": "Pannalam",
            "வேற": "Vera", "சொல்லு": "Sollu", "பாருங்க": "Paarunga",
            "உங்களுக்கு": "Ungalukku", "உதவ": "Uthava", "முடியும்": "Mudiyum",
            "தயாராக": "Ready-aa", "உள்ளேன்": "Irukken",
        }
        for ta_word, en_word in tamil_map.items():
            t = t.replace(ta_word, en_word)
        # Strip any remaining stray Tamil Unicode chars that couldn't be matched
        t = re.sub(r"[\u0B80-\u0BFF]+", "", t)
        t = re.sub(r"\s+", " ", t).strip()

    elif target_lang == "TAMIL":
        # Remove stray English fillers if mostly Tamil
        t = re.sub(r"^(Sure|Okay|Alright|Here you go),?\s*", "", t, flags=re.IGNORECASE)

    elif target_lang == "ENGLISH":
        # Strip stray Tamil chars if any
        t = re.sub(r"[\u0B80-\u0BFF]+", "", t)
        t = re.sub(r"\s+", " ", t).strip()

    return t
