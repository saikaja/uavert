-- Crime trendlines (01-03-trends.md).

-- Toronto Police Neighbourhood Crime Rates: yearly counts and rates per neighbourhood, as published.
CREATE TABLE neighbourhood_crime_years (
    neighbourhood_id integer NOT NULL REFERENCES neighbourhoods (id),
    year             integer NOT NULL,
    offence          text NOT NULL,              -- Toronto Police field name, e.g. ASSAULT
    count            integer NOT NULL,
    rate_per_100k    double precision NOT NULL,  -- per 100,000 residents in that year
    source_key       text NOT NULL REFERENCES sources (key),
    collected_at     timestamptz NOT NULL DEFAULT now(),
    last_seen_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (neighbourhood_id, year, offence)
);
