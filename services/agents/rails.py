# PharmAi Vision — Designed & developed by NIKHIL CHARY SRIRAMOJU
import re
DISCLAIMER = "\n\n*Educational information only — not medical advice. Confirm with a pharmacist or doctor.*"
DOSE = re.compile(r"\b\d+(\.\d+)?\s?(mg|mcg|g|ml|iu)\b", re.I)
def safety_check(draft: str, evidence: list):
    """Grounding rail: every dose figure in the answer must appear verbatim in retrieved evidence."""
    ev = " ".join(e["text"] for e in evidence).lower().replace(" ", "")
    bad = [m.group(0) for m in DOSE.finditer(draft) if m.group(0).lower().replace(" ", "") not in ev]
    if bad:
        return False, "I can't verify the dosing details in my sources. Please check the package insert or ask a pharmacist." + DISCLAIMER
    return True, draft + DISCLAIMER
