# PharmAi Vision — Designed & developed by NIKHIL CHARY SRIRAMOJU
"""Gateway: emergency pre-filter, async vision->agents pipeline, WebSocket streaming."""
import os, httpx, asyncio, json
from fastapi import FastAPI, UploadFile, File, WebSocket, Depends
from celery import Celery
from emergency import detect_emergency
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="PharmAi Vision Gateway"); Instrumentator().instrument(app).expose(app)
celery = Celery("g", broker=os.getenv("REDIS_URL"), backend=os.getenv("REDIS_URL"))

def current_user(): return {"id": "demo"}   # TODO: OIDC/JWT verification + set app.user_id for Postgres RLS

@app.post("/v1/identify")
async def identify(file: UploadFile = File(...), query: str = "", u=Depends(current_user)):
    if (e := detect_emergency(query)): return {"final": e, "emergency": True}
    async with httpx.AsyncClient(timeout=60) as c:
        v = (await c.post(f"{os.getenv('VISION_URL')}/identify", files={"file": (file.filename, await file.read())})).json()
    t = celery.send_task("run_agents", args=[query or "Explain this medicine", v, {}])
    return {"task_id": t.id, "vision_status": v["vision"]["status"]}

@app.get("/v1/result/{task_id}")
def result(task_id: str):
    r = celery.AsyncResult(task_id)
    return {"state": r.state, "result": r.result if r.ready() else None}

@app.websocket("/ws/chat")      # voice: client sends Whisper transcript; TTS (XTTS/ElevenLabs) consumes token stream
async def chat(ws: WebSocket):
    await ws.accept()
    while True:
        msg = json.loads(await ws.receive_text())
        if (e := detect_emergency(msg["text"])):
            await ws.send_json({"type": "emergency", "text": e}); continue
        t = celery.send_task("run_agents", args=[msg["text"], {}, msg.get("profile", {})])
        while not t.ready(): await asyncio.sleep(0.2)
        for tok in t.result["final"].split(" "): await ws.send_json({"type": "token", "text": tok + " "})
        await ws.send_json({"type": "done"})

@app.post("/v1/transcribe")      # voice -> text via Groq Whisper
async def transcribe(file: UploadFile = File(...)):
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post("https://api.groq.com/openai/v1/audio/transcriptions",
                         headers={"Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}"},
                         data={"model": os.getenv("STT_MODEL", "whisper-large-v3-turbo")},
                         files={"file": (file.filename, await file.read())})
    return r.json()
