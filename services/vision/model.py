# PharmAi Vision — Designed & developed by NIKHIL CHARY SRIRAMOJU
"""CNN (EfficientNet-B7) + ViT fusion for pill identification with multi-task heads."""
import cv2, numpy as np, torch, torch.nn as nn, timm
from dataclasses import dataclass

SHAPES = ["round","oval","capsule","oblong","square","triangle","diamond","hexagon","other"]
COLORS = ["white","yellow","orange","red","pink","brown","green","blue","purple","gray","black","multi"]

def preprocess(bgr: np.ndarray, size: int = 384) -> torch.Tensor:
    """Denoise -> CLAHE (low light) -> unsharp (blur) -> crop to pill contour -> normalise."""
    img = cv2.fastNlMeansDenoisingColored(bgr, None, 5, 5, 7, 21)
    l, a, b = cv2.split(cv2.cvtColor(img, cv2.COLOR_BGR2LAB))
    l = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(l)
    img = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)
    img = cv2.addWeighted(img, 1.6, cv2.GaussianBlur(img, (0, 0), 2.0), -0.6, 0)
    gray = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if cnts:
        x, y, w, h = cv2.boundingRect(max(cnts, key=cv2.contourArea))
        pad = int(0.1 * max(w, h)); x, y = max(0, x - pad), max(0, y - pad)
        img = img[y:y + h + 2 * pad, x:x + w + 2 * pad]
    img = cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), (size, size), interpolation=cv2.INTER_CUBIC)
    x = (img.astype(np.float32) / 255 - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
    return torch.from_numpy(x.transpose(2, 0, 1)).float().unsqueeze(0)

class PillNet(nn.Module):
    def __init__(self, n_pills: int, emb: int = 512):
        super().__init__()
        self.cnn = timm.create_model("tf_efficientnet_b7", pretrained=True, num_classes=0)
        self.vit = timm.create_model("vit_base_patch16_384", pretrained=True, num_classes=0)
        d = self.cnn.num_features + self.vit.num_features
        self.fuse = nn.Sequential(nn.Linear(d, 1024), nn.GELU(), nn.Dropout(0.3), nn.Linear(1024, emb))
        self.pill = nn.Linear(emb, n_pills)
        self.shape = nn.Linear(emb, len(SHAPES))
        self.color = nn.Linear(emb, len(COLORS))
        self.scored = nn.Linear(emb, 1)

    def forward(self, x):
        z = self.fuse(torch.cat([self.cnn(x), self.vit(x)], dim=1))
        return dict(emb=nn.functional.normalize(z, dim=1), pill=self.pill(z),
                    shape=self.shape(z), color=self.color(z), scored=self.scored(z))

@dataclass
class Candidate:
    pill_id: int; prob: float; shape: str; color: str; scored: bool

@torch.inference_mode()
def predict(model, x, k=5, temperature=1.4, accept=0.80, review=0.45):
    out = model(x)
    p = torch.softmax(out["pill"] / temperature, dim=1)[0]   # temperature-calibrated
    top = torch.topk(p, k)
    sh, co = SHAPES[int(out["shape"].argmax())], COLORS[int(out["color"].argmax())]
    sc = bool(torch.sigmoid(out["scored"])[0] > .5)
    cands = [vars(Candidate(int(i), float(v), sh, co, sc)) for v, i in zip(top.values, top.indices)]
    best = cands[0]["prob"]
    status = "accepted" if best >= accept else "needs_verification" if best >= review else "unidentified"
    return dict(status=status, candidates=cands)
