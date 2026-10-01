-- Extreme heat and big crowds (01-03-calibration-crowds-heat.md).

-- City of Toronto Heat Relief Network: places to cool down, with weekly hours.
CREATE TABLE cool_spaces (
    location_id  text PRIMARY KEY,
    region_id    integer NOT NULL REFERENCES regions (id),
    name         text NOT NULL,
    kind         text NOT NULL,                 -- e.g. Cooling Location, Cooling Centre, Indoor Pool
    address      text,
    hours        jsonb NOT NULL,                -- {"mon": ["0900", "2030"] | "call" | null, ...}
    notes        text,
    geom         geometry(Point, 4326) NOT NULL,
    collected_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX cool_spaces_geom_idx ON cool_spaces USING gist (geom);

-- Major venues (reviewed list in data/major_venues.csv).
CREATE TABLE venues (
    name         text PRIMARY KEY,
    region_id    integer NOT NULL REFERENCES regions (id),
    address      text NOT NULL,
    capacity     integer NOT NULL,
    source_url   text NOT NULL,
    geom         geometry(Point, 4326) NOT NULL,
    collected_at timestamptz NOT NULL DEFAULT now()
);

-- Large City events found in the City's Festivals & Events calendar, by date.
CREATE TABLE crowd_events (
    event_key    text NOT NULL,                 -- City calendar id
    event_date   date NOT NULL,                 -- Toronto date
    region_id    integer NOT NULL REFERENCES regions (id),
    name         text NOT NULL,
    pattern      text NOT NULL,                 -- which reviewed large-event name it matched
    location     text,
    geom         geometry(Point, 4326) NOT NULL,
    collected_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (event_key, event_date)
);
CREATE INDEX crowd_events_date_idx ON crowd_events (event_date);
