CREATE CONSTRAINT drug_rxcui IF NOT EXISTS FOR (d:Drug) REQUIRE d.rxcui IS UNIQUE;
CREATE CONSTRAINT cond_id IF NOT EXISTS FOR (c:Condition) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT se_id IF NOT EXISTS FOR (s:SideEffect) REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT pill_id IF NOT EXISTS FOR (p:Pill) REQUIRE p.id IS UNIQUE;
CREATE FULLTEXT INDEX drug_names IF NOT EXISTS FOR (d:Drug) ON EACH [d.brand, d.generic];

// Nodes: Drug{rxcui,brand,generic,strength,class,atc,form,boxed_warning,source}
//        Pill{id,shape,color,imprint[],score,ndc}  Condition{id,name}  SideEffect{id,name,severity}
//        Interaction{severity,mechanism,source}  Food / Supplement  Chunk{id,section,text,url}
// Edges: (Drug)-[:TREATS {evidence_level,source}]->(Condition)
//        (Drug)-[:CAUSES {frequency,severity}]->(SideEffect)
//        (Drug)-[:INTERACTS_WITH {severity,mechanism,source}]-(Drug|Food|Supplement)
//        (Drug)-[:CONTRAINDICATED_IN]->(Condition)   (Pill)-[:IS_FORM_OF]->(Drug)
//        (Drug)-[:HAS_CHUNK]->(Chunk)   // bridge to Qdrant point ids

// Multi-hop patient-aware context query
MATCH (d:Drug {rxcui:$rxcui})
OPTIONAL MATCH (d)-[:TREATS]->(c:Condition)
OPTIONAL MATCH (d)-[x:INTERACTS_WITH]-(o) WHERE o.rxcui IN $patient_rxcuis
OPTIONAL MATCH (d)-[:CONTRAINDICATED_IN]->(ci:Condition) WHERE ci.id IN $patient_conditions
RETURN d, collect(DISTINCT c) AS treats,
       collect(DISTINCT {with:o.generic, sev:x.severity, mech:x.mechanism}) AS interactions,
       collect(DISTINCT ci) AS contraindicated;
