-- Core schema. Conventions:
--   * every data table has collected_at (when we first fetched the row) and, where rows are
--     re-fetched, last_seen_at (when we last saw it); the data's own date is a separate column;
--   * every place-based table has region_id, so a new city is new rows, not a new schema;
--   * geometry is WGS84 (SRID 4326); grid cells are H3 resolution 9.

CREATE TABLE regions (
    id           serial PRIMARY KEY,
    code         text NOT NULL UNIQUE,          -- e.g. CA-ON-TOR
    name         text NOT NULL,
    country      text NOT NULL,                 -- ISO 3166-1 alpha-2
    timezone     text NOT NULL,
    collected_at timestamptz NOT NULL DEFAULT now()
);

-- One row per data source: licence, attribution and freshness shown in the app.
CREATE TABLE sources (
    key               text PRIMARY KEY,
    name              text NOT NULL,
    url               text NOT NULL,
    licence           text NOT NULL,
    attribution       text NOT NULL,
    data_as_of        timestamptz,              -- newest date the data itself refers to
    last_collected_at timestamptz,              -- last successful collection
    last_status       text CHECK (last_status IN ('ok', 'failed')),
    last_error        text,
    collected_at      timestamptz NOT NULL DEFAULT now()
);

-- Permanent history of every collection run; rows are only ever added.
CREATE TABLE ingest_runs (
    id           bigserial PRIMARY KEY,
    source_key   text NOT NULL REFERENCES sources (key),
    started_at   timestamptz NOT NULL,
    finished_at  timestamptz,
    status       text NOT NULL CHECK (status IN ('running', 'ok', 'failed')),
    rows_written integer,
    data_as_of   timestamptz,
    error        text
);
CREATE INDEX ingest_runs_source_idx ON ingest_runs (source_key, started_at DESC);

CREATE TABLE neighbourhoods (
    id           serial PRIMARY KEY,
    region_id    integer NOT NULL REFERENCES regions (id),
    external_id  text NOT NULL,                 -- Toronto: HOOD_158
    name         text NOT NULL,
    population   integer,
    valid_year   integer NOT NULL,              -- year the population and counts refer to
    counts       jsonb NOT NULL DEFAULT '{}',   -- published counts for valid_year, e.g. {"THEFTFROMMV": 120}
    geom         geometry(MultiPolygon, 4326) NOT NULL,
    collected_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (region_id, external_id)
);
CREATE INDEX neighbourhoods_geom_idx ON neighbourhoods USING gist (geom);

-- Statistics Canada Crime Severity Index weights, one set per edition.
CREATE TABLE csi_weights (
    edition      text NOT NULL,
    offence_key  text NOT NULL,
    label        text NOT NULL,
    weight       numeric NOT NULL CHECK (weight > 0),
    source_url   text NOT NULL,
    retrieved_on date NOT NULL,
    collected_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (edition, offence_key)
);

-- Maps each source offence (UCR code + extension; '*' matches any) to a CSI offence.
CREATE TABLE offence_map (
    source_key      text NOT NULL,
    ucr_code        text NOT NULL,
    ucr_ext         text NOT NULL,
    offence_label   text NOT NULL,
    csi_offence_key text NOT NULL,
    match           text NOT NULL CHECK (match IN ('exact', 'closest')),
    group_label     text NOT NULL,              -- plain-language group used in reasons, e.g. "robberies"
    note            text,
    collected_at    timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (source_key, ucr_code, ucr_ext)
);

-- Individual reported crimes. One row per source record; scoring counts each event once.
CREATE TABLE incidents (
    id               bigserial PRIMARY KEY,
    region_id        integer NOT NULL REFERENCES regions (id),
    source_key       text NOT NULL REFERENCES sources (key),
    event_id         text NOT NULL,
    ucr_code         text NOT NULL,
    ucr_ext          text NOT NULL,
    offence          text NOT NULL,
    csi_offence_key  text NOT NULL,
    premises_type    text,                      -- null when the source doesn't record it
    occurred_at      timestamptz NOT NULL,
    hood_external_id text,
    geom             geometry(Point, 4326),     -- null when the source gives no location
    h3               h3index,
    collected_at     timestamptz NOT NULL DEFAULT now(),
    last_seen_at     timestamptz NOT NULL DEFAULT now(),
    UNIQUE (source_key, event_id, ucr_code, ucr_ext)
);
CREATE INDEX incidents_event_idx ON incidents (event_id);
CREATE INDEX incidents_occurred_idx ON incidents (occurred_at);
CREATE INDEX incidents_h3_idx ON incidents (h3);

-- The street grid: every H3 resolution-9 cell whose centre lies in a neighbourhood.
CREATE TABLE cells (
    h3              h3index PRIMARY KEY,
    region_id       integer NOT NULL REFERENCES regions (id),
    neighbourhood_id integer NOT NULL REFERENCES neighbourhoods (id),
    geom            geometry(Polygon, 4326) NOT NULL,
    centre          geometry(Point, 4326) NOT NULL,
    collected_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX cells_geom_idx ON cells USING gist (geom);
CREATE INDEX cells_neighbourhood_idx ON cells (neighbourhood_id);

-- Crime scores computed in advance by `uavert build-scores`.
CREATE TABLE neighbourhood_scores (
    neighbourhood_id integer PRIMARY KEY REFERENCES neighbourhoods (id),
    weighted_rate    double precision NOT NULL,
    crime_score      integer NOT NULL CHECK (crime_score BETWEEN 0 AND 100),
    reasons          jsonb NOT NULL,
    details          jsonb NOT NULL,            -- per-group counts and rates behind the score
    sources_used     jsonb NOT NULL,            -- {source_key: {as_of, collected_at}} at compute time
    computed_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE cell_scores (
    h3             h3index PRIMARY KEY REFERENCES cells (h3),
    incident_count integer NOT NULL,            -- street incidents in the cell and its 6 neighbours
    own_value      double precision NOT NULL,
    local_value    double precision NOT NULL,
    smoothed_value double precision NOT NULL,
    crime_score    integer NOT NULL CHECK (crime_score BETWEEN 0 AND 100),
    reasons        jsonb NOT NULL,
    sources_used   jsonb NOT NULL,
    computed_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE aqhi_readings (
    station_id   text NOT NULL,
    station_name text NOT NULL,
    region_id    integer NOT NULL REFERENCES regions (id),
    geom         geometry(Point, 4326) NOT NULL,
    observed_at  timestamptz NOT NULL,
    aqhi         numeric NOT NULL,
    collected_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (station_id, observed_at)
);

CREATE TABLE official_alerts (
    id           bigserial PRIMARY KEY,
    region_id    integer NOT NULL REFERENCES regions (id),
    source_key   text NOT NULL REFERENCES sources (key),
    external_id  text NOT NULL,
    alert_type   text NOT NULL,                 -- warning | watch | advisory | statement
    alert_code   text,
    name         text NOT NULL,
    risk_colour  text,                          -- yellow | orange | red
    status       text NOT NULL,                 -- as published, e.g. active | ended
    issued_at    timestamptz NOT NULL,
    expires_at   timestamptz,
    text         text,
    geom         geometry(Geometry, 4326) NOT NULL,
    collected_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (source_key, external_id)
);
CREATE INDEX official_alerts_geom_idx ON official_alerts USING gist (geom);

-- News reports. Only the headline, link and time are stored, never article text.
CREATE TABLE news_events (
    id            bigserial PRIMARY KEY,
    region_id     integer NOT NULL REFERENCES regions (id),
    source_key    text NOT NULL REFERENCES sources (key),
    url           text NOT NULL UNIQUE,
    headline      text NOT NULL,
    publisher     text NOT NULL,
    category      text NOT NULL CHECK (category IN ('protest', 'violent_incident')),
    location_text text,
    geom          geometry(Point, 4326),        -- null means citywide (no usable location)
    h3            h3index,
    published_at  timestamptz NOT NULL,
    collected_at  timestamptz NOT NULL DEFAULT now(),
    last_seen_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX news_events_published_idx ON news_events (published_at DESC);
