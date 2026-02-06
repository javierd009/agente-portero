-- Add usage limits for credentials / QR tokens (single-use vs multi-use)
-- 2026-02-05

-- Generic: allow single-use or N-uses, defined by user
ALTER TABLE access_credentials
  ADD COLUMN IF NOT EXISTS max_uses INTEGER,
  ADD COLUMN IF NOT EXISTS use_count INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_access_credentials_max_uses ON access_credentials(max_uses);

COMMENT ON COLUMN access_credentials.max_uses IS 'NULL = unlimited within validity window; 1 = single-use; N = N uses';
COMMENT ON COLUMN access_credentials.use_count IS 'How many times the credential has been used (validated)';

-- QR tokens: optional mirror (kept for convenience)
ALTER TABLE qr_tokens
  ADD COLUMN IF NOT EXISTS max_uses INTEGER,
  ADD COLUMN IF NOT EXISTS use_count INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_qr_tokens_max_uses ON qr_tokens(max_uses);

COMMENT ON COLUMN qr_tokens.max_uses IS 'NULL = unlimited; 1 = single-use; N = N uses';
COMMENT ON COLUMN qr_tokens.use_count IS 'Usage count for this token';
