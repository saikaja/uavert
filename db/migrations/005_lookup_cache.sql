-- Saved address and route lookups (01-03-solidify.md), so restarts and new hosted instances
-- reuse earlier answers instead of calling the free outside services again.

CREATE TABLE geocode_cache (
    query_key    text PRIMARY KEY,              -- normalised search text
    found        boolean NOT NULL,
    display_name text,
    lon          double precision,
    lat          double precision,
    collected_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE route_cache (
    route_key    text PRIMARY KEY,              -- "lon,lat;lon,lat", 5 decimals (about 1 m)
    coordinates  jsonb NOT NULL,
    distance_m   double precision NOT NULL,
    duration_s   double precision NOT NULL,
    collected_at timestamptz NOT NULL DEFAULT now()
);
