-- Agente Portero - Initial Schema
-- Multi-tenant SaaS for Virtual Guard System

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- TABLES
-- ============================================

-- Condominiums (Tenants)
CREATE TABLE IF NOT EXISTS condominiums (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    address TEXT,
    timezone TEXT DEFAULT 'America/Mexico_City',
    settings JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_condominiums_slug ON condominiums(slug);
CREATE INDEX idx_condominiums_is_active ON condominiums(is_active);

-- Residents
CREATE TABLE IF NOT EXISTS residents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominium_id UUID NOT NULL REFERENCES condominiums(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    unit TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    whatsapp TEXT,
    authorized_visitors JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_residents_condominium ON residents(condominium_id);
CREATE INDEX idx_residents_unit ON residents(unit);
CREATE INDEX idx_residents_user ON residents(user_id);

-- Agents (Virtual Guards)
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominium_id UUID NOT NULL REFERENCES condominiums(id) ON DELETE CASCADE,
    name TEXT DEFAULT 'Agente Virtual',
    extension TEXT NOT NULL,
    prompt TEXT DEFAULT '',
    voice_id TEXT,
    language TEXT DEFAULT 'es-MX',
    is_active BOOLEAN DEFAULT true,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_agents_condominium ON agents(condominium_id);
CREATE INDEX idx_agents_extension ON agents(extension);

-- Visitors
CREATE TABLE IF NOT EXISTS visitors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominium_id UUID NOT NULL REFERENCES condominiums(id) ON DELETE CASCADE,
    resident_id UUID REFERENCES residents(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    id_number TEXT,
    phone TEXT,
    vehicle_plate TEXT,
    reason TEXT,
    authorized_by TEXT,
    entry_time TIMESTAMPTZ,
    exit_time TIMESTAMPTZ,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_visitors_condominium ON visitors(condominium_id);
CREATE INDEX idx_visitors_resident ON visitors(resident_id);
CREATE INDEX idx_visitors_status ON visitors(status);
CREATE INDEX idx_visitors_plate ON visitors(vehicle_plate);

-- Vehicles
CREATE TABLE IF NOT EXISTS vehicles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominium_id UUID NOT NULL REFERENCES condominiums(id) ON DELETE CASCADE,
    resident_id UUID REFERENCES residents(id) ON DELETE CASCADE,
    plate TEXT NOT NULL,
    brand TEXT,
    model TEXT,
    color TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_vehicles_condominium ON vehicles(condominium_id);
CREATE INDEX idx_vehicles_plate ON vehicles(plate);
CREATE INDEX idx_vehicles_resident ON vehicles(resident_id);

-- Access Logs
CREATE TABLE IF NOT EXISTS access_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominium_id UUID NOT NULL REFERENCES condominiums(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    access_point TEXT NOT NULL,
    direction TEXT,
    resident_id UUID REFERENCES residents(id) ON DELETE SET NULL,
    visitor_id UUID REFERENCES visitors(id) ON DELETE SET NULL,
    visitor_name TEXT,
    vehicle_plate TEXT,
    authorization_method TEXT NOT NULL,
    authorized_by UUID,
    camera_snapshot_url TEXT,
    confidence_score FLOAT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_access_logs_condominium ON access_logs(condominium_id);
CREATE INDEX idx_access_logs_event_type ON access_logs(event_type);
CREATE INDEX idx_access_logs_created_at ON access_logs(created_at DESC);
CREATE INDEX idx_access_logs_plate ON access_logs(vehicle_plate);

-- Camera Events
CREATE TABLE IF NOT EXISTS camera_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominium_id UUID NOT NULL REFERENCES condominiums(id) ON DELETE CASCADE,
    camera_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    plate_number TEXT,
    plate_confidence FLOAT,
    face_id TEXT,
    face_confidence FLOAT,
    snapshot_url TEXT,
    video_clip_url TEXT,
    processed BOOLEAN DEFAULT false,
    matched_resident_id UUID REFERENCES residents(id) ON DELETE SET NULL,
    matched_vehicle_id UUID REFERENCES vehicles(id) ON DELETE SET NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_camera_events_condominium ON camera_events(condominium_id);
CREATE INDEX idx_camera_events_camera ON camera_events(camera_id);
CREATE INDEX idx_camera_events_type ON camera_events(event_type);
CREATE INDEX idx_camera_events_plate ON camera_events(plate_number);
CREATE INDEX idx_camera_events_created_at ON camera_events(created_at DESC);

-- Notifications
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominium_id UUID NOT NULL REFERENCES condominiums(id) ON DELETE CASCADE,
    resident_id UUID REFERENCES residents(id) ON DELETE SET NULL,
    channel TEXT NOT NULL,
    recipient TEXT NOT NULL,
    notification_type TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    error_message TEXT,
    related_visitor_id UUID REFERENCES visitors(id) ON DELETE SET NULL,
    related_access_log_id UUID REFERENCES access_logs(id) ON DELETE SET NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_notifications_condominium ON notifications(condominium_id);
CREATE INDEX idx_notifications_resident ON notifications(resident_id);
CREATE INDEX idx_notifications_status ON notifications(status);
CREATE INDEX idx_notifications_created_at ON notifications(created_at DESC);

-- ============================================
-- ROW LEVEL SECURITY (Multi-tenant Isolation)
-- ============================================

ALTER TABLE condominiums ENABLE ROW LEVEL SECURITY;
ALTER TABLE residents ENABLE ROW LEVEL SECURITY;
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE visitors ENABLE ROW LEVEL SECURITY;
ALTER TABLE vehicles ENABLE ROW LEVEL SECURITY;
ALTER TABLE access_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE camera_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

-- Policies for service role (backend) - full access
CREATE POLICY "Service role has full access to condominiums"
    ON condominiums FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role has full access to residents"
    ON residents FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role has full access to agents"
    ON agents FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role has full access to visitors"
    ON visitors FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role has full access to vehicles"
    ON vehicles FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role has full access to access_logs"
    ON access_logs FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role has full access to camera_events"
    ON camera_events FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role has full access to notifications"
    ON notifications FOR ALL
    USING (auth.role() = 'service_role');

-- Policies for authenticated users (residents)
-- Residents can only see data from their own condominium

CREATE POLICY "Users can view their own condominium"
    ON condominiums FOR SELECT
    USING (
        id IN (
            SELECT condominium_id FROM residents
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can view residents in their condominium"
    ON residents FOR SELECT
    USING (
        condominium_id IN (
            SELECT condominium_id FROM residents
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update their own resident record"
    ON residents FOR UPDATE
    USING (user_id = auth.uid());

CREATE POLICY "Users can view agents in their condominium"
    ON agents FOR SELECT
    USING (
        condominium_id IN (
            SELECT condominium_id FROM residents
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can view visitors in their condominium"
    ON visitors FOR SELECT
    USING (
        condominium_id IN (
            SELECT condominium_id FROM residents
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can create visitors for their condominium"
    ON visitors FOR INSERT
    WITH CHECK (
        condominium_id IN (
            SELECT condominium_id FROM residents
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can view vehicles in their condominium"
    ON vehicles FOR SELECT
    USING (
        condominium_id IN (
            SELECT condominium_id FROM residents
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can manage their own vehicles"
    ON vehicles FOR ALL
    USING (
        resident_id IN (
            SELECT id FROM residents
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can view access logs in their condominium"
    ON access_logs FOR SELECT
    USING (
        condominium_id IN (
            SELECT condominium_id FROM residents
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can view camera events in their condominium"
    ON camera_events FOR SELECT
    USING (
        condominium_id IN (
            SELECT condominium_id FROM residents
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can view their own notifications"
    ON notifications FOR SELECT
    USING (
        resident_id IN (
            SELECT id FROM residents
            WHERE user_id = auth.uid()
        )
    );

-- ============================================
-- FUNCTIONS
-- ============================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_condominiums_updated_at
    BEFORE UPDATE ON condominiums
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_residents_updated_at
    BEFORE UPDATE ON residents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agents_updated_at
    BEFORE UPDATE ON agents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_visitors_updated_at
    BEFORE UPDATE ON visitors
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_vehicles_updated_at
    BEFORE UPDATE ON vehicles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
