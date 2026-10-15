-- The website's read-only database user (01-03-security.md). The role itself is created with SQL by
-- scripts/create_web_role.py (not through Neon's console or API, which would add neon_superuser rights).
-- Grants apply only where the role exists. A new table the website must WRITE needs its own grant in its migration.

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'uavert_web') THEN
        GRANT USAGE ON SCHEMA public TO uavert_web;
        GRANT SELECT ON ALL TABLES IN SCHEMA public TO uavert_web;
        -- The only tables the website writes: saved address and route answers.
        GRANT INSERT, UPDATE ON geocode_cache, route_cache TO uavert_web;
        -- Tables added later by migrations (run as the owner) are readable too.
        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO uavert_web;
    END IF;
END
$$;
