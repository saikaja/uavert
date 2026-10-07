-- Time of day (01-03-time-of-day.md).

-- How many people are out at each hour, relative to the daytime average (data/activity_by_hour.csv).
CREATE TABLE activity_by_hour (
    hour              smallint PRIMARY KEY CHECK (hour BETWEEN 0 AND 23),
    pedestrian_factor real,                     -- measured hours only
    bikeshare_factor  real NOT NULL,
    factor_used       real NOT NULL CHECK (factor_used > 0),
    basis             text NOT NULL CHECK (basis IN ('measured', 'estimated')),
    retrieved_on      date NOT NULL,
    collected_at      timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE cell_scores
    ADD COLUMN crime_score_by_hour smallint[],  -- 24 scores, index 1 = midnight hour
    ADD COLUMN intensity_by_hour   real[];      -- incidents at that hour vs the block's average hour
