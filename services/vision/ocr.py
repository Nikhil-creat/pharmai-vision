# PharmAi Vision — Designed & developed by NIKHIL CHARY SRIRAMOJU
"""Imprint / NDC / expiry OCR: PaddleOCR (detect+recognise); swap in fine-tuned TrOCR for embossed pharma fonts."""
import re
from paddleocr import PaddleOCR
_ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
NDC = re.compile(r"\b\d{4,5}-\d{3,4}-\d{1,2}\b")
EXP = re.compile(r"(?:EXP|EXPIRY|USE BY)[:\s]*([0-1]?\d[/\-.]\d{2,4})", re.I)

def read_text(bgr):
    res = _ocr.ocr(bgr, cls=True)[0] or []
    toks = [(t, c) for _, (t, c) in res if c > 0.5]
    raw = " ".join(t for t, _ in toks)
    m = EXP.search(raw)
    return dict(imprint=[t.upper() for t, _ in toks if 1 <= len(t) <= 8], ndc=NDC.findall(raw),
                expiry=m.group(1) if m else None, confidence=sum(c for _, c in toks) / max(len(toks), 1))
