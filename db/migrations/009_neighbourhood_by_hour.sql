-- Time of day on the neighbourhood map (01-03-time-map.md).

ALTER TABLE neighbourhood_scores
    ADD COLUMN crime_score_by_hour smallint[],  -- 24 scores, index 1 = midnight hour
    ADD COLUMN move_by_hour        real[];      -- the typical street cell's move at that hour, before capping
