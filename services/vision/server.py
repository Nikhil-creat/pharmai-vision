# PharmAi Vision — Designed & developed by NIKHIL CHARY SRIRAMOJU
import cv2, numpy as np, torch, os
from fastapi import FastAPI, UploadFile
from prometheus_fastapi_instrumentator import Instrumentator
from model import PillNet, preprocess, predict
from ocr import read_text

app = FastAPI(title="vision"); Instrumentator().instrument(app).expose(app)
model = PillNet(int(os.getenv("N_PILLS", "5000")))
if os.path.exists("/models/pillnet.pt"):
    model.load_state_dict(torch.load("/models/pillnet.pt", map_location="cpu"))
model.eval()

@app.post("/identify")
async def identify(file: UploadFile):
    bgr = cv2.imdecode(np.frombuffer(await file.read(), np.uint8), cv2.IMREAD_COLOR)
    return dict(vision=predict(model, preprocess(bgr)), ocr=read_text(bgr))

@app.get("/healthz")
def health(): return {"ok": True}
