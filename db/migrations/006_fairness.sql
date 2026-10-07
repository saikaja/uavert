-- Fairness check (01-03-solidify.md): do neighbourhood crime scores mostly follow income?

CREATE TABLE neighbourhood_census (
    region_id               integer NOT NULL REFERENCES regions (id),
    external_id             text NOT NULL,      -- same numbering as neighbourhoods.external_id
    median_household_income numeric,            -- dollars, income year census_year - 1
    low_income_pct          numeric,            -- LIM-AT prevalence, %
    census_year             integer NOT NULL,
    collected_at            timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (region_id, external_id)
);

-- One row per score build, so the history of the check is kept.
CREATE TABLE fairness_checks (
    id             bigserial PRIMARY KEY,
    computed_at    timestamptz NOT NULL DEFAULT now(),
    rho_income     double precision,              -- Spearman: crime score vs median household income
    rho_low_income double precision,              -- Spearman: crime score vs low-income share
    n              integer NOT NULL,              -- neighbourhoods with census data
    label          text NOT NULL,
    census_year    integer NOT NULL
);
