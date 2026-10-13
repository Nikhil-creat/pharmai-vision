# PharmAi Vision — Designed & developed by NIKHIL CHARY SRIRAMOJU
import re
PATTERNS = [r"overdos|took too many|swallowed (a lot|too many)|poison",
            r"anaphyla|throat (is )?(closing|swelling)|can'?t breathe|difficulty breathing|face swelling",
            r"chest pain|seizure|unconscious|not breathing|suicid|kill myself|end my life"]
MSG = ("EMERGENCY: This may be life-threatening. Call your local emergency number NOW "
       "(US 911 · EU 112 · UK 999 · India 112). US Poison Control: 1-800-222-1222. "
       "If you're thinking of self-harm, call/text 988 (US). Don't wait for this app.")
def detect_emergency(text: str):
    t = (text or "").lower()
    return MSG if any(re.search(p, t) for p in PATTERNS) else None
