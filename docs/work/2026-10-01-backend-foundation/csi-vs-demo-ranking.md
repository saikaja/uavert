# Neighbourhood ranking: demo weights vs StatCan CSI weights

*Generated 2026-10-01 12:30. Scores computed 2026-10-01 16:30 UTC; Toronto Police data collected 2026-10-01 16:27 UTC.*

## How the two are calculated

- **Demo (September 29, 2026):** Toronto Police's published 2025 rates per 100,000, weighted by hand: homicide 10, shootings 5, assault 3, robbery 3, break and enter 2, auto theft 1, theft over $5,000 1, theft from vehicles 1, bicycle theft 0.5.
- **CSI (this build):** every 2025 incident weighted by its Statistics Canada Crime Severity Index weight (2009 published table): murder 7,042, discharging a firearm 988, robbery 583, aggravated assault 405, break and enter 187, theft over $5,000 139, auto theft 84, assault with a weapon 77, common assault 23, thefts under $5,000 37. Each event is counted once across the Toronto Police datasets.

Both are ranked across the 158 neighbourhoods (0 = lowest, 100 = highest).

## Summary

- **75 of 158 neighbourhoods change band.**
- **Biggest shift:** under CSI, common assault counts for much less (23 against robbery's 583), and homicides and shootings count for much more. Areas with many assaults but few robberies, shootings or homicides drop; areas with robberies, shootings or homicides rise.

## Top 15 under CSI

| Neighbourhood | Demo rank | Demo score | CSI rank | CSI score | Change |
|---|---|---|---|---|---|
| Yonge-Bay Corridor | 2 | 99 (high) | 1 | 100 (high) | +1 |
| University | 6 | 97 (high) | 2 | 99 (high) | +4 |
| Kensington-Chinatown | 3 | 99 (high) | 3 | 99 (high) | +0 |
| West Humber-Clairville | 7 | 96 (high) | 4 | 98 (high) | +3 |
| Yorkdale-Glen Park | 9 | 95 (high) | 5 | 97 (high) | +4 |
| Humber Summit | 13 | 92 (high) | 6 | 97 (high) | +7 |
| Moss Park | 5 | 97 (high) | 7 | 96 (high) | -2 |
| Bendale-Glen Andrew | 28 | 83 (high) | 8 | 96 (high) | +20 |
| Downtown Yonge East | 4 | 98 (high) | 9 | 95 (high) | -5 |
| York University Heights | 8 | 96 (high) | 10 | 94 (high) | -2 |
| Oakdale-Beverley Heights | 16 | 90 (high) | 11 | 94 (high) | +5 |
| Kennedy Park | 10 | 94 (high) | 12 | 93 (high) | -2 |
| Annex | 22 | 87 (high) | 13 | 92 (high) | +9 |
| Etobicoke City Centre | 26 | 84 (high) | 14 | 92 (high) | +12 |
| Milliken | 58 | 64 (elevated) | 15 | 91 (high) | +43 |

## Top 15 under the demo weights

| Neighbourhood | Demo rank | Demo score | CSI rank | CSI score | Change |
|---|---|---|---|---|---|
| Mimico-Queensway | 1 | 100 (high) | 19 | 89 (high) | -18 |
| Yonge-Bay Corridor | 2 | 99 (high) | 1 | 100 (high) | +1 |
| Kensington-Chinatown | 3 | 99 (high) | 3 | 99 (high) | +0 |
| Downtown Yonge East | 4 | 98 (high) | 9 | 95 (high) | -5 |
| Moss Park | 5 | 97 (high) | 7 | 96 (high) | -2 |
| University | 6 | 97 (high) | 2 | 99 (high) | +4 |
| West Humber-Clairville | 7 | 96 (high) | 4 | 98 (high) | +3 |
| York University Heights | 8 | 96 (high) | 10 | 94 (high) | -2 |
| Yorkdale-Glen Park | 9 | 95 (high) | 5 | 97 (high) | +4 |
| Kennedy Park | 10 | 94 (high) | 12 | 93 (high) | -2 |
| Playter Estates-Danforth | 11 | 94 (high) | 24 | 85 (high) | -13 |
| Danforth | 12 | 93 (high) | 20 | 88 (high) | -8 |
| Humber Summit | 13 | 92 (high) | 6 | 97 (high) | +7 |
| West Hill | 14 | 92 (high) | 17 | 90 (high) | -3 |
| Wexford/Maryvale | 15 | 91 (high) | 16 | 90 (high) | -1 |

## 15 biggest movers

Positive change = ranks riskier under CSI.

| Neighbourhood | Demo rank | Demo score | CSI rank | CSI score | Change |
|---|---|---|---|---|---|
| Bridle Path-Sunnybrook-York Mills | 133 | 16 (lower) | 46 | 71 (elevated) | +87 |
| Rustic | 50 | 69 (elevated) | 136 | 14 (lower) | -86 |
| Bayview Woods-Steeles | 137 | 13 (lower) | 63 | 61 (elevated) | +74 |
| O'Connor-Parkview | 76 | 52 (elevated) | 143 | 10 (lower) | -67 |
| Agincourt South-Malvern West | 80 | 50 (elevated) | 22 | 87 (high) | +58 |
| Mount Dennis | 98 | 38 (moderate) | 41 | 75 (high) | +57 |
| Princess-Rosethorn | 127 | 20 (lower) | 75 | 53 (elevated) | +52 |
| Islington | 119 | 25 (moderate) | 68 | 57 (elevated) | +51 |
| Woodbine Corridor | 91 | 43 (moderate) | 141 | 11 (lower) | -50 |
| Oakwood Village | 105 | 34 (moderate) | 150 | 5 (lower) | -45 |
| Clairlea-Birchmount | 17 | 90 (high) | 61 | 62 (elevated) | -44 |
| Markland Wood | 122 | 23 (lower) | 78 | 51 (elevated) | +44 |
| Milliken | 58 | 64 (elevated) | 15 | 91 (high) | +43 |
| Wychwood | 63 | 61 (elevated) | 21 | 87 (high) | +42 |
| Oakridge | 20 | 88 (high) | 62 | 61 (elevated) | -42 |

## Lowest 10 under CSI

| Neighbourhood | Demo rank | Demo score | CSI rank | CSI score | Change |
|---|---|---|---|---|---|
| Danforth East York | 134 | 15 (lower) | 149 | 6 (lower) | -15 |
| Oakwood Village | 105 | 34 (moderate) | 150 | 5 (lower) | -45 |
| Humber Bay Shores | 136 | 14 (lower) | 151 | 4 (lower) | -15 |
| Etobicoke West Mall | 128 | 19 (lower) | 152 | 4 (lower) | -24 |
| Avondale | 132 | 17 (lower) | 153 | 3 (lower) | -21 |
| Broadview North | 118 | 25 (moderate) | 154 | 3 (lower) | -36 |
| South Eglinton-Davisville | 147 | 7 (lower) | 155 | 2 (lower) | -8 |
| Forest Hill North | 151 | 4 (lower) | 156 | 1 (lower) | -5 |
| Westminster-Branson | 130 | 18 (lower) | 157 | 1 (lower) | -27 |
| Lambton Baby Point | 158 | 0 (lower) | 158 | 0 (lower) | +0 |

## Why the biggest movers moved (checked by hand, data collected 2026-10-01)

| Neighbourhood | What drives its CSI score |
|---|---|
| Bridle Path-Sunnybrook-York Mills (rises 87 places) | 48 break-ins (50% of its weighted total), 6 robberies, 2 shootings, in a population of 11,654. CSI weights a break-in 8 times a common assault (187 vs 23); the demo weighted it lower than an assault (2 vs 3). |
| Bayview Woods-Steeles (rises 74) and Mount Dennis (rises 57) | One homicide each, which makes up 30–35% of their weighted totals. This is the "one homicide outweighs about 300 assaults" effect flagged in the design. |
| Rustic (drops 86) | Mostly assaults (83, 36% of its weighted total), which CSI weights lightly, and no shootings or homicides. |

**Things to decide while testing:** whether a single homicide should move a small neighbourhood this far. Options include showing a three-year average for homicides, or pointing out the small-number effect in the reasons. These are tuning choices for the resident testing in the build plan; this build keeps the published weights unchanged.
