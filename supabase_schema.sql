-- =============================================================================
-- AGENTE PORTERO - SUPABASE DATABASE SCHEMA
-- Ejecutar este SQL completo en Supabase SQL Editor
-- =============================================================================

-- Habilitar extensión UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- TABLAS
-- =============================================================================

-- Tabla condominiums
CREATE TABLE condominiums (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    address TEXT,
    phone VARCHAR(50),
    timezone VARCHAR(50) DEFAULT 'America/Mexico_City',
    settings JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Tabla agents (Agentes de voz AI)
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominium_id UUID REFERENCES condominiums(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    extension VARCHAR(50),
    prompt TEXT,
    voice_id VARCHAR(50),
    language VARCHAR(10) DEFAULT 'es-MX',
    is_active BOOLEAN DEFAULT true,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Tabla residents
CREATE TABLE residents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominium_id UUID REFERENCES condominiums(id) ON DELETE CASCADE,
    user_id UUID,
    name VARCHAR(255) NOT NULL,
    unit VARCHAR(50) NOT NULL,
    phone VARCHAR(50),
    email VARCHAR(255),
    whatsapp VARCHAR(50),
    authorized_visitors TEXT[] DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Tabla visitors
CREATE TABLE visitors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominium_id UUID REFERENCES condominiums(id) ON DELETE CASCADE,
    resident_id UUID REFERENCES residents(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    id_number VARCHAR(100),
    phone VARCHAR(50),
    vehicle_plate VARCHAR(50),
    reason TEXT,
    authorized_by VARCHAR(50),
    valid_until TIMESTAMP,
    notes TEXT,
    entry_time TIMESTAMP,
    exit_time TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Tabla vehicles
CREATE TABLE vehicles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominium_id UUID REFERENCES condominiums(id) ON DELETE CASCADE,
    resident_id UUID REFERENCES residents(id) ON DELETE CASCADE,
    plate VARCHAR(50) NOT NULL,
    brand VARCHAR(100),
    model VARCHAR(100),
    color VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Tabla access_logs
CREATE TABLE access_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominium_id UUID REFERENCES condominiums(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    access_point VARCHAR(100),
    direction VARCHAR(20),
    resident_id UUID REFERENCES residents(id) ON DELETE SET NULL,
    visitor_id UUID REFERENCES visitors(id) ON DELETE SET NULL,
    visitor_name VARCHAR(255),
    vehicle_plate VARCHAR(50),
    authorization_method VARCHAR(50),
    authorized_by VARCHAR(255),
    camera_snapshot_url TEXT,
    confidence_score FLOAT,
    extra_data JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Tabla reports
CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominium_id UUID REFERENCES condominiums(id) ON DELETE CASCADE,
    resident_id UUID REFERENCES residents(id) ON DELETE SET NULL,
    report_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    location VARCHAR(255),
    urgency VARCHAR(50) DEFAULT 'normal',
    status VARCHAR(50) DEFAULT 'pending',
    source VARCHAR(50) DEFAULT 'web',
    photo_urls JSONB DEFAULT '[]',
    assigned_to VARCHAR(255),
    resolved_at TIMESTAMP,
    resolution_notes TEXT,
    extra_data JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Tabla camera_events
CREATE TABLE camera_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominium_id UUID REFERENCES condominiums(id) ON DELETE CASCADE,
    camera_id VARCHAR(100) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    detected_plate VARCHAR(50),
    confidence FLOAT,
    snapshot_url TEXT,
    extra_data JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Tabla notifications
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominium_id UUID REFERENCES condominiums(id) ON DELETE CASCADE,
    resident_id UUID REFERENCES residents(id) ON DELETE SET NULL,
    channel VARCHAR(50) NOT NULL,
    recipient VARCHAR(255) NOT NULL,
    notification_type VARCHAR(50),
    title VARCHAR(255),
    message TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    sent_at TIMESTAMP,
    delivered_at TIMESTAMP,
    extra_data JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- =============================================================================
-- ÍNDICES (para performance)
-- =============================================================================

CREATE INDEX idx_residents_whatsapp ON residents(whatsapp);
CREATE INDEX idx_residents_condominium ON residents(condominium_id);
CREATE INDEX idx_access_logs_created_at ON access_logs(created_at DESC);
CREATE INDEX idx_access_logs_condominium ON access_logs(condominium_id);
CREATE INDEX idx_reports_status ON reports(status);
CREATE INDEX idx_reports_condominium ON reports(condominium_id);
CREATE INDEX idx_camera_events_created_at ON camera_events(created_at DESC);
CREATE INDEX idx_notifications_status ON notifications(status);

-- =============================================================================
-- ROW LEVEL SECURITY (Multi-tenant isolation)
-- =============================================================================

ALTER TABLE condominiums ENABLE ROW LEVEL SECURITY;
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE residents ENABLE ROW LEVEL SECURITY;
ALTER TABLE visitors ENABLE ROW LEVEL SECURITY;
ALTER TABLE vehicles ENABLE ROW LEVEL SECURITY;
ALTER TABLE access_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE camera_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

-- Políticas básicas (ajustar según necesidades)
CREATE POLICY "Enable all for service role" ON condominiums FOR ALL USING (true);
CREATE POLICY "Enable all for service role" ON agents FOR ALL USING (true);
CREATE POLICY "Enable all for service role" ON residents FOR ALL USING (true);
CREATE POLICY "Enable all for service role" ON visitors FOR ALL USING (true);
CREATE POLICY "Enable all for service role" ON vehicles FOR ALL USING (true);
CREATE POLICY "Enable all for service role" ON access_logs FOR ALL USING (true);
CREATE POLICY "Enable all for service role" ON reports FOR ALL USING (true);
CREATE POLICY "Enable all for service role" ON camera_events FOR ALL USING (true);
CREATE POLICY "Enable all for service role" ON notifications FOR ALL USING (true);

-- =============================================================================
-- SEED DATA (Datos de prueba)
-- =============================================================================

-- Insertar condominio de ejemplo
INSERT INTO condominiums (name, slug, address, timezone, settings, is_active)
VALUES (
    'Residencial del Valle',
    'residencial-del-valle',
    'Av. Principal 1234, Monterrey, NL, México',
    'America/Mexico_City',
    '{"gate_api_url": "http://192.168.1.100", "cameras": ["cam_01", "cam_02"]}'::jsonb,
    true
);

-- Insertar residentes de ejemplo (con WhatsApp reales para testing)
INSERT INTO residents (condominium_id, name, unit, phone, email, whatsapp, is_active)
SELECT
    c.id,
    'Juan Pérez García',
    'A-101',
    '+52 81 1234 5678',
    'juan.perez@email.com',
    '5218112345678',
    true
FROM condominiums c WHERE c.slug = 'residencial-del-valle';

INSERT INTO residents (condominium_id, name, unit, phone, email, whatsapp, is_active)
SELECT
    c.id,
    'María López Hernández',
    'B-205',
    '+52 81 8765 4321',
    'maria.lopez@email.com',
    '5218187654321',
    true
FROM condominiums c WHERE c.slug = 'residencial-del-valle';

INSERT INTO residents (condominium_id, name, unit, phone, email, whatsapp, is_active)
SELECT
    c.id,
    'Carlos Rodríguez Martínez',
    'C-102',
    '+52 81 5555 6666',
    'carlos.rodriguez@email.com',
    '5218155556666',
    true
FROM condominiums c WHERE c.slug = 'residencial-del-valle';

-- Insertar vehículos de ejemplo
INSERT INTO vehicles (condominium_id, resident_id, plate, brand, model, color, is_active)
SELECT
    c.id,
    r.id,
    'ABC123',
    'Toyota',
    'Corolla 2022',
    'Blanco',
    true
FROM condominiums c, residents r
WHERE c.slug = 'residencial-del-valle' AND r.unit = 'A-101';

INSERT INTO vehicles (condominium_id, resident_id, plate, brand, model, color, is_active)
SELECT
    c.id,
    r.id,
    'XYZ789',
    'Honda',
    'Civic 2023',
    'Negro',
    true
FROM condominiums c, residents r
WHERE c.slug = 'residencial-del-valle' AND r.unit = 'B-205';

-- Insertar agente AI de ejemplo
INSERT INTO agents (condominium_id, name, extension, prompt, voice_id, language, is_active, settings)
SELECT
    c.id,
    'Agente Principal',
    '100',
    'Eres un guardia de seguridad virtual profesional y amable del condominio Residencial del Valle. Tu trabajo es verificar visitantes, autorizar accesos y ayudar a los residentes.',
    'alloy',
    'es-MX',
    true,
    '{"temperature": 0.8, "max_tokens": 150}'::jsonb
FROM condominiums c WHERE c.slug = 'residencial-del-valle';

-- Insertar visitantes de ejemplo
INSERT INTO visitors (condominium_id, resident_id, name, vehicle_plate, reason, authorized_by, valid_until, status)
SELECT
    c.id,
    r.id,
    'Pedro Sánchez',
    'DEF456',
    'Visita familiar',
    'whatsapp',
    NOW() + INTERVAL '2 hours',
    'approved'
FROM condominiums c, residents r
WHERE c.slug = 'residencial-del-valle' AND r.unit = 'A-101';

-- Insertar reportes de ejemplo
INSERT INTO reports (condominium_id, resident_id, report_type, title, description, location, urgency, status, source)
SELECT
    c.id,
    r.id,
    'maintenance',
    'Luz del pasillo fundida',
    'La luz del pasillo del edificio A no funciona desde ayer',
    'Edificio A, 1er piso',
    'normal',
    'pending',
    'whatsapp'
FROM condominiums c, residents r
WHERE c.slug = 'residencial-del-valle' AND r.unit = 'A-101';

INSERT INTO reports (condominium_id, resident_id, report_type, title, description, location, urgency, status, source)
SELECT
    c.id,
    r.id,
    'security',
    'Portón de estacionamiento abierto',
    'El portón del estacionamiento no cierra correctamente',
    'Estacionamiento principal',
    'high',
    'in_progress',
    'voice'
FROM condominiums c, residents r
WHERE c.slug = 'residencial-del-valle' AND r.unit = 'B-205';

INSERT INTO reports (condominium_id, resident_id, report_type, title, description, location, urgency, status, source)
SELECT
    c.id,
    r.id,
    'cleaning',
    'Basura acumulada',
    'Hay basura acumulada en el área de reciclaje',
    'Área de reciclaje',
    'low',
    'resolved',
    'web'
FROM condominiums c, residents r
WHERE c.slug = 'residencial-del-valle' AND r.unit = 'C-102';

-- =============================================================================
-- VERIFICACIÓN
-- =============================================================================

-- Ver todas las tablas creadas
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

-- Contar registros en cada tabla
SELECT
    'condominiums' as tabla, COUNT(*) as registros FROM condominiums
UNION ALL SELECT 'residents', COUNT(*) FROM residents
UNION ALL SELECT 'agents', COUNT(*) FROM agents
UNION ALL SELECT 'vehicles', COUNT(*) FROM vehicles
UNION ALL SELECT 'visitors', COUNT(*) FROM visitors
UNION ALL SELECT 'reports', COUNT(*) FROM reports;
