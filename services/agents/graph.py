# PharmAi Vision — Designed & developed by NIKHIL CHARY SRIRAMOJU
"""LangGraph multi-agent orchestration: routing, tools, bounded reflection loop, fallback."""
import os, operator
from typing import TypedDict, Annotated, Optional
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
import graph_retrieval as hs
from emergency import detect_emergency
from rails import safety_check

llm = ChatOpenAI(base_url=os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1"),
                 api_key=os.getenv("GROQ_API_KEY") or os.getenv("LLM_API_KEY", "x"),
                 model=os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"), temperature=0)

class State(TypedDict, total=False):
    query: str; vision: dict; profile: dict; drug: Optional[dict]
    evidence: list; interactions: list; draft: str; critique: str; retries: int; final: str
    trace: Annotated[list, operator.add]

def vision_verify(s: State):
    """Vision Verification Agent: cross-check CNN candidates vs DB shape/colour/imprint."""
    best, v = None, s.get("vision", {})
    for c in v.get("vision", {}).get("candidates", []):
        db = hs.get_pill_attrs(c["pill_id"])
        score = c["prob"] + .15 * (db["shape"] == c["shape"]) + .15 * (db["color"] == c["color"]) \
                + .3 * bool(set(db["imprint"] or []) & set(v.get("ocr", {}).get("imprint", [])))
        if not best or score > best[0]: best = (score, db)
    ok = bool(best and best[0] >= 0.9)
    return {"drug": best[1] if ok else None, "trace": ["verify:ok" if ok else "verify:ambiguous"]}

def clinical_rag(s: State):
    d = s.get("drug") or {}
    ev = hs.search(d.get("generic_name") or s["query"], rxcui=d.get("rxcui"), k=8)
    return {"evidence": ev, "trace": [f"rag:{len(ev)}"]}

def interaction_audit(s: State):
    meds = s.get("profile", {}).get("current_meds", [])
    hits = hs.graph_interactions(s["drug"]["rxcui"], meds) if s.get("drug") and meds else []
    return {"interactions": hits, "trace": [f"interactions:{len(hits)}"]}

def patient_dosage(s: State):
    ctx = {k: s.get("profile", {}).get(k) for k in ("age", "pregnant", "lactating", "egfr", "hepatic")}
    cites = "\n".join(f"[{i}] {e['text']} ({e.get('source')})" for i, e in enumerate(s["evidence"]))
    prompt = (f"Answer ONLY from the evidence, cite as [n]; if absent say 'not found in sources'. Never invent doses.\n"
              f"Sections: Identification; Why used; How/when/how long; Missed dose & overdose; Safety (boxed warnings, "
              f"side effects, interactions {s.get('interactions')}); Special populations for {ctx}; Storage & disposal.\n"
              f"Evidence:\n{cites}\nQuestion: {s['query']}\nPrior critique: {s.get('critique', 'none')}")
    return {"draft": llm.invoke(prompt).content, "trace": ["draft"]}

def reflect(s: State):
    v = llm.invoke(f"List unsupported/unsafe claims in DRAFT vs EVIDENCE. Reply 'OK' if none.\nDRAFT:\n{s['draft']}\nEVIDENCE:\n{s['evidence']}").content
    return {"critique": v, "retries": s.get("retries", 0) + 1, "trace": ["reflect"]}

def safety(s: State):
    ok, text = safety_check(s["draft"], s["evidence"])
    return {"final": text, "trace": [f"safety:{ok}"]}

def fallback(s: State):
    return {"final": "I couldn't identify or verify this confidently. Share the imprint code, a clearer photo, or the "
                     "package, or ask a pharmacist. US Poison Control: 1-800-222-1222.", "trace": ["fallback"]}

def after_verify(s): return "rag" if (s.get("drug") or not s.get("vision")) else "fallback"
def after_reflect(s):
    if s["critique"].strip().upper().startswith("OK"): return "safety"
    return "draft" if s["retries"] < 2 else "fallback"

g = StateGraph(State)
for n, f in [("verify", vision_verify), ("rag", clinical_rag), ("interact", interaction_audit),
             ("draft", patient_dosage), ("reflect", reflect), ("safety", safety), ("fallback", fallback)]:
    g.add_node(n, f)
g.set_entry_point("verify")
g.add_conditional_edges("verify", after_verify, {"rag": "rag", "fallback": "fallback"})
g.add_edge("rag", "interact"); g.add_edge("interact", "draft"); g.add_edge("draft", "reflect")
g.add_conditional_edges("reflect", after_reflect, {"safety": "safety", "draft": "draft", "fallback": "fallback"})
g.add_edge("safety", END); g.add_edge("fallback", END)
app = g.compile()

def run(query, vision=None, profile=None):
    if (e := detect_emergency(query)): return {"final": e, "trace": ["emergency"]}   # bypasses LLM entirely
    return app.invoke({"query": query, "vision": vision or {}, "profile": profile or {}, "retries": 0, "trace": []})
