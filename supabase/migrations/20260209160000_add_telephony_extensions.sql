-- Add telephony extension mapping for intercom/bot routing (multi-tenant)

CREATE TABLE IF NOT EXISTS tenant_telephony_extensions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  condominium_id UUID NOT NULL REFERENCES condominiums(id) ON DELETE CASCADE,

  -- FreePBX/intercom extension that was called (e.g., 1004, 1005)
  extension TEXT NOT NULL,

  -- Logical access point
  access_point TEXT NOT NULL, -- vehicular_entry | vehicular_exit | pedestrian

  -- How to open (kept generic; secrets stay in env)
  device_type TEXT NOT NULL, -- panel | biometric
  device_host TEXT NOT NULL,
  door_id INT NOT NULL DEFAULT 1,

  enabled BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE (condominium_id, extension)
);

CREATE INDEX IF NOT EXISTS idx_tenant_telephony_extensions_condo ON tenant_telephony_extensions(condominium_id);
CREATE INDEX IF NOT EXISTS idx_tenant_telephony_extensions_ext ON tenant_telephony_extensions(extension);
CREATE INDEX IF NOT EXISTS idx_tenant_telephony_extensions_enabled ON tenant_telephony_extensions(enabled);

ALTER TABLE tenant_telephony_extensions ENABLE ROW LEVEL SECURITY;

-- service role full access
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'tenant_telephony_extensions' AND policyname = 'Service role has full access to tenant_telephony_extensions'
  ) THEN
    CREATE POLICY "Service role has full access to tenant_telephony_extensions"
      ON tenant_telephony_extensions FOR ALL
      USING (auth.role() = 'service_role');
  END IF;
END $$;

-- authenticated users can view their condo mappings
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'tenant_telephony_extensions' AND policyname = 'Users can view telephony extensions in their condominium'
  ) THEN
    CREATE POLICY "Users can view telephony extensions in their condominium"
      ON tenant_telephony_extensions FOR SELECT
      USING (
        auth.uid() IS NOT NULL AND
        condominium_id IN (
          SELECT condominium_id FROM residents WHERE user_id = auth.uid()
        )
      );
  END IF;
END $$;
