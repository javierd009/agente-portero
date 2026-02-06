-- Access credentials + audit logs (scalable foundation)
-- 2026-02-05

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ------------------------------------------------------------
-- 1) access_credentials: generic credential layer (QR now, PIN/plate/face later)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS access_credentials (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  condominium_id UUID NOT NULL REFERENCES condominiums(id) ON DELETE CASCADE,

  -- Subject
  resident_id UUID REFERENCES residents(id) ON DELETE SET NULL,
  visitor_id UUID REFERENCES visitors(id) ON DELETE SET NULL,

  -- Credential type
  credential_type TEXT NOT NULL, -- qr | pin | plate | face | card

  -- Permission scope
  allowed_access_points JSONB NOT NULL DEFAULT '[]'::jsonb,

  -- Validity
  valid_from TIMESTAMPTZ DEFAULT NOW(),
  valid_until TIMESTAMPTZ,

  -- Lifecycle
  status TEXT NOT NULL DEFAULT 'active', -- active | used | revoked | expired
  used_at TIMESTAMPTZ,
  revoked_at TIMESTAMPTZ,

  -- Provisioning
  provisioning_mode TEXT NOT NULL DEFAULT 'backend', -- backend | device
  device_target JSONB DEFAULT '{}'::jsonb, -- e.g. {"panel_ip":"172.20.22.3","door":1}

  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_access_credentials_condominium ON access_credentials(condominium_id);
CREATE INDEX IF NOT EXISTS idx_access_credentials_visitor ON access_credentials(visitor_id);
CREATE INDEX IF NOT EXISTS idx_access_credentials_resident ON access_credentials(resident_id);
CREATE INDEX IF NOT EXISTS idx_access_credentials_status ON access_credentials(status);
CREATE INDEX IF NOT EXISTS idx_access_credentials_valid_until ON access_credentials(valid_until);

ALTER TABLE access_credentials ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename='access_credentials'
      AND policyname='Service role has full access to access_credentials'
  ) THEN
    CREATE POLICY "Service role has full access to access_credentials"
      ON access_credentials FOR ALL
      USING (auth.role() = 'service_role');
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename='access_credentials'
      AND policyname='Users can view access_credentials in their condominium'
  ) THEN
    CREATE POLICY "Users can view access_credentials in their condominium"
      ON access_credentials FOR SELECT
      USING (
        condominium_id IN (
          SELECT condominium_id FROM residents WHERE user_id = auth.uid()
        )
      );
  END IF;
END $$;

-- updated_at trigger
CREATE OR REPLACE FUNCTION update_access_credentials_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS access_credentials_updated_at ON access_credentials;
CREATE TRIGGER access_credentials_updated_at
  BEFORE UPDATE ON access_credentials
  FOR EACH ROW
  EXECUTE FUNCTION update_access_credentials_updated_at();

-- ------------------------------------------------------------
-- 2) Link qr_tokens -> access_credentials (optional but preferred)
-- ------------------------------------------------------------
ALTER TABLE qr_tokens
  ADD COLUMN IF NOT EXISTS credential_id UUID REFERENCES access_credentials(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_qr_tokens_credential ON qr_tokens(credential_id);

-- ------------------------------------------------------------
-- 3) audit_logs: who did what, when (agent/operator/resident)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  condominium_id UUID NOT NULL REFERENCES condominiums(id) ON DELETE CASCADE,

  actor_type TEXT NOT NULL, -- resident | operator | agent | api_key
  actor_id TEXT,
  actor_label TEXT,

  action TEXT NOT NULL, -- issue_qr | revoke_credential | open_gate | create_visitor | etc.
  resource_type TEXT,
  resource_id UUID,

  status TEXT NOT NULL DEFAULT 'success', -- success | failure
  message TEXT,
  metadata JSONB DEFAULT '{}'::jsonb,

  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_condominium_created ON audit_logs(condominium_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);

ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename='audit_logs'
      AND policyname='Service role has full access to audit_logs'
  ) THEN
    CREATE POLICY "Service role has full access to audit_logs"
      ON audit_logs FOR ALL
      USING (auth.role() = 'service_role');
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename='audit_logs'
      AND policyname='Users can view audit_logs in their condominium'
  ) THEN
    CREATE POLICY "Users can view audit_logs in their condominium"
      ON audit_logs FOR SELECT
      USING (
        condominium_id IN (
          SELECT condominium_id FROM residents WHERE user_id = auth.uid()
        )
      );
  END IF;
END $$;
