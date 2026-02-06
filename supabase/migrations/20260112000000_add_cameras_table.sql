-- Add cameras table for VMS functionality
-- Stores Hikvision camera configurations per condominium

CREATE TABLE IF NOT EXISTS cameras (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    condominium_id UUID NOT NULL REFERENCES condominiums(id) ON DELETE CASCADE,

    -- Basic info
    name VARCHAR(100) NOT NULL,
    location VARCHAR(200),

    -- Connection
    host VARCHAR(255) NOT NULL,
    port INTEGER DEFAULT 80,
    username VARCHAR(100) NOT NULL,
    password VARCHAR(255) NOT NULL,

    -- Camera type and capabilities
    camera_type VARCHAR(50) DEFAULT 'hikvision',
    has_ptz BOOLEAN DEFAULT FALSE,
    has_anpr BOOLEAN DEFAULT FALSE,
    has_face BOOLEAN DEFAULT FALSE,

    -- Stream URLs
    rtsp_main TEXT,
    rtsp_sub TEXT,
    snapshot_url TEXT,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_online BOOLEAN DEFAULT FALSE,
    last_seen TIMESTAMP WITH TIME ZONE,

    -- Settings (JSON)
    settings JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_cameras_condominium ON cameras(condominium_id);
CREATE INDEX IF NOT EXISTS idx_cameras_active ON cameras(is_active);

-- RLS (Row Level Security)
ALTER TABLE cameras ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see cameras from their condominium
CREATE POLICY "cameras_tenant_isolation" ON cameras
    FOR ALL
    USING (condominium_id IN (
        SELECT id FROM condominiums WHERE id = condominium_id
    ));

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_cameras_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER cameras_updated_at
    BEFORE UPDATE ON cameras
    FOR EACH ROW
    EXECUTE FUNCTION update_cameras_updated_at();

-- Comments
COMMENT ON TABLE cameras IS 'Hikvision camera configurations for VMS';
COMMENT ON COLUMN cameras.camera_type IS 'hikvision, dahua, generic';
COMMENT ON COLUMN cameras.has_anpr IS 'Automatic Number Plate Recognition capability';
