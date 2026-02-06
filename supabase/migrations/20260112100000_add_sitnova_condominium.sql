-- Create Sitnova condominium and admin user linkage
-- Run after creating admin@integratec-cr.com in Supabase Auth

-- 1. Create Sitnova condominium
INSERT INTO condominiums (id, name, slug, address, timezone, is_active)
VALUES (
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    'Residencial Sitnova',
    'sitnova',
    'Costa Rica',
    'America/Costa_Rica',
    true
) ON CONFLICT (slug) DO NOTHING;

-- 2. Create admin resident record
-- Note: You need to replace USER_ID_HERE with the actual user ID from Supabase Auth
-- After creating the user in Supabase Auth, get their ID and run:
-- UPDATE residents SET user_id = 'actual-uuid-from-auth' WHERE name = 'Administrador';

INSERT INTO residents (
    condominium_id,
    name,
    unit,
    email,
    is_active
) VALUES (
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    'Administrador',
    'ADMIN',
    'admin@integratec-cr.com',
    true
) ON CONFLICT DO NOTHING;

-- Comment for manual step
COMMENT ON TABLE residents IS 'After running this migration, update the admin resident user_id:
1. Go to Supabase Dashboard → Authentication → Users
2. Create user: admin@integratec-cr.com with password Integratec20@
3. Copy the user UUID
4. Run: UPDATE residents SET user_id = ''YOUR-UUID-HERE'' WHERE email = ''admin@integratec-cr.com'';
';
