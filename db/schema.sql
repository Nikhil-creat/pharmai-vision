CREATE EXTENSION IF NOT EXISTS pgcrypto; CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email_hash BYTEA UNIQUE NOT NULL,        -- HMAC(email) for lookup
  email_enc BYTEA NOT NULL,                -- AES-256-GCM with per-user DEK
  dek_wrapped BYTEA NOT NULL,              -- DEK wrapped by KMS KEK (delete = crypto-shred for GDPR erasure)
  role TEXT NOT NULL DEFAULT 'patient' CHECK (role IN ('patient','caregiver','clinician','admin')),
  consent_health_data BOOLEAN NOT NULL DEFAULT FALSE, consent_at TIMESTAMPTZ,
  region TEXT NOT NULL DEFAULT 'EU', created_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE user_profiles (               -- PHI as encrypted JSON {age,pregnant,egfr,conditions,meds}
  user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  phi_enc BYTEA NOT NULL, updated_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE pills (                       -- Pill Physical Attributes Master
  id SERIAL PRIMARY KEY, rxcui TEXT NOT NULL, ndc TEXT, brand TEXT, generic TEXT NOT NULL, strength TEXT,
  shape TEXT, color TEXT, imprint TEXT[], score_lines SMALLINT DEFAULT 0, size_mm NUMERIC(4,1),
  coating TEXT, dosage_form TEXT, manufacturer TEXT, image_ref TEXT, source TEXT, updated_at TIMESTAMPTZ DEFAULT now());
CREATE INDEX pills_imprint_gin ON pills USING GIN (imprint);
CREATE INDEX pills_attrs ON pills (shape, color);
CREATE TABLE search_logs (
  id BIGSERIAL PRIMARY KEY, user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  image_sha256 BYTEA, query_redacted TEXT, vision_status TEXT, top_pill_id INT REFERENCES pills(id),
  confidence REAL, latency_ms INT, emergency BOOLEAN DEFAULT FALSE, created_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE agent_audit (                 -- append-only, hash-chained (row_hash = H(prev_hash || row))
  id BIGSERIAL PRIMARY KEY, request_id UUID NOT NULL, agent TEXT NOT NULL, model_version TEXT,
  input_digest BYTEA, output_digest BYTEA, evidence_ids TEXT[], guardrail_verdict TEXT,
  prev_hash BYTEA, row_hash BYTEA, created_at TIMESTAMPTZ DEFAULT now());
CREATE RULE audit_no_update AS ON UPDATE TO agent_audit DO INSTEAD NOTHING;
CREATE RULE audit_no_delete AS ON DELETE TO agent_audit DO INSTEAD NOTHING;
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY own_profile ON user_profiles USING (user_id = current_setting('app.user_id')::uuid);
ALTER TABLE search_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY own_logs ON search_logs USING (user_id = current_setting('app.user_id')::uuid);
