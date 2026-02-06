-- Add visitor authorization fields + QR tokens
-- 2026-02-05

-- Ensure extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ------------------------------------------------------------
-- 1) Visitors: add columns needed for user-defined validity + door scoping
-- ------------------------------------------------------------
ALTER TABLE visitors
  ADD COLUMN IF NOT EXISTS valid_until TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS authorization_type TEXT DEFAULT 'manual',
  ADD COLUMN IF NOT EXISTS allowed_access_points JSONB DEFAULT '[]'::jsonb;

CREATE INDEX IF NOT EXISTS idx_visitors_valid_until ON visitors(valid_until);

COMMENT ON COLUMN visitors.valid_until IS 'Authorization expiry time (user-defined)';
COMMENT ON COLUMN visitors.authorization_type IS 'uber | airbnb | employee | guest | delivery | manual';
COMMENT ON COLUMN visitors.allowed_access_points IS 'JSON array of access points allowed (e.g. ["vehicular_entry","vehicular_exit","pedestrian"])';

-- ------------------------------------------------------------
-- 2) QR tokens: signed tokens with TTL + usage tracking
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS qr_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  condominium_id UUID NOT NULL REFERENCES condominiums(id) ON DELETE CASCADE,
  resident_id UUID REFERENCES residents(id) ON DELETE SET NULL,
  visitor_id UUID REFERENCES visitors(id) ON DELETE SET NULL,

  -- Token payload
  token TEXT UNIQUE NOT NULL,
  purpose TEXT DEFAULT 'visitor_access',
  allowed_access_points JSONB DEFAULT '[]'::jsonb,

  -- TTL / usage
  issued_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL,
  used_at TIMESTAMPTZ,
  revoked_at TIMESTAMPTZ,

  metadata JSONB DEFAULT '{}'::jsonb,

  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_qr_tokens_condominium ON qr_tokens(condominium_id);
CREATE INDEX IF NOT EXISTS idx_qr_tokens_token ON qr_tokens(token);
CREATE INDEX IF NOT EXISTS idx_qr_tokens_expires ON qr_tokens(expires_at);
CREATE INDEX IF NOT EXISTS idx_qr_tokens_visitor ON qr_tokens(visitor_id);

-- ------------------------------------------------------------
-- RLS
-- ------------------------------------------------------------
ALTER TABLE qr_tokens ENABLE ROW LEVEL SECURITY;

-- Service role full access
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename='qr_tokens'
      AND policyname='Service role has full access to qr_tokens'
  ) THEN
    CREATE POLICY "Service role has full access to qr_tokens"
      ON qr_tokens FOR ALL
      USING (auth.role() = 'service_role');
  END IF;
END $$;

-- Authenticated users: view tokens within their condominium
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename='qr_tokens'
      AND policyname='Users can view qr_tokens in their condominium'
  ) THEN
    CREATE POLICY "Users can view qr_tokens in their condominium"
      ON qr_tokens FOR SELECT
      USING (
        condominium_id IN (
          SELECT condominium_id FROM residents WHERE user_id = auth.uid()
        )
      );
  END IF;
END $$;
