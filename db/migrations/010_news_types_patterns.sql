-- News by type of event, and patterns in police reports (01-03-news.md). Information only: neither affects a score.

ALTER TABLE news_events DROP CONSTRAINT news_events_category_check;
ALTER TABLE news_events ADD CONSTRAINT news_events_category_check
    CHECK (category IN ('protest', 'violent_incident', 'property_crime'));

-- Neighbourhoods where an offence ran well above its usual level in the latest 30 days of police data.
-- Rebuilt by `uavert build-scores`.
CREATE TABLE crime_patterns (
    neighbourhood_id  integer NOT NULL REFERENCES neighbourhoods (id),
    offence           text NOT NULL,              -- CSI offence key, e.g. break_and_enter
    recent            integer NOT NULL,           -- incidents in the latest 30 days
    usual_per_30_days real NOT NULL,              -- the 12 months before, per 30 days
    chance            double precision NOT NULL,  -- Poisson chance of at least `recent` at the usual level
    first_date        date NOT NULL,              -- the 30 days covered
    last_date         date NOT NULL,
    source_key        text NOT NULL REFERENCES sources (key),
    computed_at       timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (neighbourhood_id, offence)
);
