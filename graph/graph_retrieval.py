# PharmAi Vision — Designed & developed by NIKHIL CHARY SRIRAMOJU
"""Hybrid retrieval: Qdrant dense + BM25 sparse + Neo4j graph expansion -> RRF -> cross-encoder rerank.
Chunking: one SPL section per chunk (<=400 tokens, 60 overlap); payload = rxcui, section, source, url, text."""
import os
from neo4j import GraphDatabase
from qdrant_client import QdrantClient, models
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, CrossEncoder

emb = SentenceTransformer("BAAI/bge-small-en-v1.5")              # swap for a biomedical encoder
rerank = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")    # or Cohere Rerank
qd = QdrantClient(url=os.getenv("QDRANT_URL", "http://qdrant:6333"))
neo = GraphDatabase.driver(os.getenv("NEO4J_URI", "bolt://neo4j:7687"), auth=("neo4j", os.getenv("NEO4J_PASSWORD", "")))
COLL = "drug_chunks"

def rrf(lists, k=60):
    sc = {}
    for lst in lists:
        for r, d in enumerate(lst): sc.setdefault(d["id"], [d, 0])[1] += 1 / (k + r + 1)
    return [v[0] for v in sorted(sc.values(), key=lambda v: -v[1])]

def search(query, rxcui=None, k=8):
    flt = models.Filter(must=[models.FieldCondition(key="rxcui", match=models.MatchValue(value=rxcui))]) if rxcui else None
    dense = [dict(id=h.id, **h.payload) for h in qd.search(COLL, emb.encode(query).tolist(), query_filter=flt, limit=30)]
    pool = [dict(id=p.id, **p.payload) for p in qd.scroll(COLL, scroll_filter=flt, limit=500)[0]]
    sparse = []
    if pool:
        scores = BM25Okapi([p["text"].lower().split() for p in pool]).get_scores(query.lower().split())
        sparse = [pool[i] for i in scores.argsort()[::-1][:30]]
    graph = []
    if rxcui:
        with neo.session() as s:
            ids = [r["id"] for r in s.run("MATCH (d:Drug {rxcui:$r})-[:INTERACTS_WITH|TREATS*1..2]-(n)-[:HAS_CHUNK]->(c) "
                                          "RETURN c.id AS id LIMIT 20", r=rxcui)]
        graph = [dict(id=p.id, **p.payload) for p in qd.retrieve(COLL, ids)] if ids else []
    fused = rrf([dense, sparse, graph])[:40]
    if not fused: return []
    sc = rerank.predict([(query, d["text"]) for d in fused])
    return [d for d, _ in sorted(zip(fused, sc), key=lambda x: -x[1])][:k]

def get_pill_attrs(pill_id):
    with neo.session() as s:
        r = s.run("MATCH (p:Pill {id:$i})-[:IS_FORM_OF]->(d:Drug) RETURN p.shape AS shape,p.color AS color,"
                  "p.imprint AS imprint,d.rxcui AS rxcui,d.generic AS generic_name", i=pill_id).single()
    return dict(r) if r else dict(shape=None, color=None, imprint=[], rxcui=None, generic_name=None)

def graph_interactions(rxcui, patient_rxcuis):
    with neo.session() as s:
        return [dict(r) for r in s.run("MATCH (d:Drug {rxcui:$r})-[x:INTERACTS_WITH]-(o:Drug) WHERE o.rxcui IN $m "
                "RETURN o.generic AS with, x.severity AS severity, x.mechanism AS mechanism, x.source AS source",
                r=rxcui, m=patient_rxcuis)]
