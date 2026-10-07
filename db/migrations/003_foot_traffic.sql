-- Foot traffic (design revision 3) and "compared with surroundings" (revision 2).

-- City of Toronto intersection counts: the most recent count at each location.
CREATE TABLE foot_traffic_counts (
    location_key  text PRIMARY KEY,             -- centreline type and id, e.g. "2:13468217"
    region_id     integer NOT NULL REFERENCES regions (id),
    location_name text NOT NULL,
    count_id      text NOT NULL,
    count_date    date NOT NULL,
    hours         numeric NOT NULL,             -- 8 or 14 hours counted
    pedestrians   integer NOT NULL,
    bikes         integer NOT NULL,
    vehicles      integer NOT NULL,
    geom          geometry(Point, 4326) NOT NULL,
    h3            h3index NOT NULL,
    collected_at  timestamptz NOT NULL DEFAULT now(),
    last_seen_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX foot_traffic_counts_h3_idx ON foot_traffic_counts (h3);

ALTER TABLE cell_scores
    ADD COLUMN foot_traffic_per_hour   double precision,
    ADD COLUMN foot_traffic_counts_used integer,
    ADD COLUMN foot_traffic_first_date date,
    ADD COLUMN foot_traffic_last_date  date,
    ADD COLUMN per_person_value        double precision,
    ADD COLUMN vs_surroundings         double precision,  -- null when the surroundings have no incidents
    ADD COLUMN busy_area               boolean NOT NULL DEFAULT false;
