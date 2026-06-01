CREATE TABLE IF NOT EXISTS calls (
  call_id TEXT PRIMARY KEY,
  started_at TEXT,
  ended_at TEXT,
  mc_number TEXT,
  carrier_name TEXT,
  carrier_eligibility TEXT,
  eligibility_reason TEXT,
  load_id TEXT,
  reference_number TEXT,
  origin TEXT,
  destination TEXT,
  pickup_datetime TEXT,
  delivery_datetime TEXT,
  equipment_type TEXT,
  loadboard_rate NUMERIC,
  offer_rate NUMERIC,
  final_rate NUMERIC,
  negotiation_rounds INTEGER NOT NULL DEFAULT 0,
  transfer_status TEXT,
  call_outcome TEXT,
  carrier_sentiment TEXT,
  decline_reason TEXT,
  notes TEXT,
  transcript TEXT,
  duration_seconds INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS call_events (
  id BIGSERIAL PRIMARY KEY,
  call_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS offer_evaluations (
  id BIGSERIAL PRIMARY KEY,
  call_id TEXT,
  load_id TEXT,
  reference_number TEXT,
  loadboard_rate NUMERIC NOT NULL,
  offer_rate NUMERIC NOT NULL,
  negotiation_round INTEGER NOT NULL,
  decision TEXT NOT NULL,
  counter_rate NUMERIC,
  accepted_rate NUMERIC,
  walkaway_rate NUMERIC NOT NULL,
  reason TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS api_keys (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  prefix TEXT NOT NULL UNIQUE,
  key_hash TEXT NOT NULL UNIQUE,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  scopes TEXT[] NOT NULL DEFAULT ARRAY['happyrobot'],
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_used_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_calls_updated_at ON calls (updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_calls_outcome ON calls (call_outcome);
CREATE INDEX IF NOT EXISTS idx_calls_sentiment ON calls (carrier_sentiment);
CREATE INDEX IF NOT EXISTS idx_call_events_call_id ON call_events (call_id);
CREATE INDEX IF NOT EXISTS idx_offer_evaluations_call_id ON offer_evaluations (call_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys (prefix);
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys (active);

ALTER TABLE calls ADD COLUMN IF NOT EXISTS duration_seconds INTEGER;
