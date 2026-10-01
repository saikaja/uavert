# Neighbourhood ranking: demo weights vs StatCan CSI weights

*Generated 2026-10-01 14:11. Scores computed 2026-10-01 18:11 UTC; Toronto Police data collected 2026-10-01 18:11 UTC.*

## How the two are calculated

- **Demo (September 29, 2026):** Toronto Police's published 2025 rates per 100,000, weighted by hand: homicide 10, shootings 5, assault 3, robbery 3, break and enter 2, auto theft 1, theft over $5,000 1, theft from vehicles 1, bicycle theft 0.5.
- **CSI (this build):** every 2025 incident weighted by its Statistics Canada Crime Severity Index weight (2009 published table): murder 7,042, discharging a firearm 988, robbery 583, aggravated assault 405, break and enter 187, theft over $5,000 139, auto theft 84, assault with a weapon 77, common assault 23, thefts under $5,000 37. Each event is counted once across the Toronto Police datasets, and homicides use the 2023-2025 average (3 years) so a single homicide doesn't swing a small neighbourhood.

Both are ranked across the 158 neighbourhoods (0 = lowest, 100 = highest).

## Summary

- **67 of 158 neighbourhoods change band.**
- **Biggest shift:** under CSI, common assault counts for much less (23 against robbery's 583), and homicides and shootings count for much more. Areas with many assaults but few robberies, shootings or homicides drop; areas with robberies, shootings or homicides rise.

## Top 15 under CSI

| Neighbourhood | Demo rank | Demo score | CSI rank | CSI score | Change |
|---|---|---|---|---|---|
| Yonge-Bay Corridor | 2 | 99 (high) | 1 | 100 (high) | +1 |
| Kensington-Chinatown | 3 | 99 (high) | 2 | 99 (high) | +1 |
| University | 6 | 97 (high) | 3 | 99 (high) | +3 |
| West Humber-Clairville | 7 | 96 (high) | 4 | 98 (high) | +3 |
| Moss Park | 5 | 97 (high) | 5 | 97 (high) | +0 |
| Humber Summit | 13 | 92 (high) | 6 | 97 (high) | +7 |
| Downtown Yonge East | 4 | 98 (high) | 7 | 96 (high) | -3 |
| Yorkdale-Glen Park | 9 | 95 (high) | 8 | 96 (high) | +1 |
| Bendale-Glen Andrew | 28 | 83 (high) | 9 | 95 (high) | +19 |
| York University Heights | 8 | 96 (high) | 10 | 94 (high) | -2 |
| Etobicoke City Centre | 26 | 84 (high) | 11 | 94 (high) | +15 |
| Oakdale-Beverley Heights | 16 | 90 (high) | 12 | 93 (high) | +4 |
| Milliken | 58 | 64 (elevated) | 13 | 92 (high) | +45 |
| Wexford/Maryvale | 15 | 91 (high) | 14 | 92 (high) | +1 |
| Beechborough-Greenbrook | 61 | 62 (elevated) | 15 | 91 (high) | +46 |

## Top 15 under the demo weights

| Neighbourhood | Demo rank | Demo score | CSI rank | CSI score | Change |
|---|---|---|---|---|---|
| Mimico-Queensway | 1 | 100 (high) | 17 | 90 (high) | -16 |
| Yonge-Bay Corridor | 2 | 99 (high) | 1 | 100 (high) | +1 |
| Kensington-Chinatown | 3 | 99 (high) | 2 | 99 (high) | +1 |
| Downtown Yonge East | 4 | 98 (high) | 7 | 96 (high) | -3 |
| Moss Park | 5 | 97 (high) | 5 | 97 (high) | +0 |
| University | 6 | 97 (high) | 3 | 99 (high) | +3 |
| West Humber-Clairville | 7 | 96 (high) | 4 | 98 (high) | +3 |
| York University Heights | 8 | 96 (high) | 10 | 94 (high) | -2 |
| Yorkdale-Glen Park | 9 | 95 (high) | 8 | 96 (high) | +1 |
| Kennedy Park | 10 | 94 (high) | 20 | 88 (high) | -10 |
| Playter Estates-Danforth | 11 | 94 (high) | 26 | 84 (high) | -15 |
| Danforth | 12 | 93 (high) | 50 | 69 (elevated) | -38 |
| Humber Summit | 13 | 92 (high) | 6 | 97 (high) | +7 |
| West Hill | 14 | 92 (high) | 18 | 89 (high) | -4 |
| Wexford/Maryvale | 15 | 91 (high) | 14 | 92 (high) | +1 |

## 15 biggest movers

Positive change = ranks riskier under CSI.

| Neighbourhood | Demo rank | Demo score | CSI rank | CSI score | Change |
|---|---|---|---|---|---|
| Bridle Path-Sunnybrook-York Mills | 133 | 16 (lower) | 54 | 66 (elevated) | +79 |
| Blake-Jones | 102 | 36 (moderate) | 33 | 80 (high) | +69 |
| Princess-Rosethorn | 127 | 20 (lower) | 60 | 62 (elevated) | +67 |
| Rustic | 50 | 69 (elevated) | 113 | 29 (moderate) | -63 |
| O'Connor-Parkview | 76 | 52 (elevated) | 133 | 16 (lower) | -57 |
| Woodbine Corridor | 91 | 43 (moderate) | 145 | 8 (lower) | -54 |
| Clairlea-Birchmount | 17 | 90 (high) | 67 | 58 (elevated) | -50 |
| Agincourt North | 143 | 10 (lower) | 94 | 41 (moderate) | +49 |
| Taylor-Massey | 59 | 63 (elevated) | 108 | 32 (moderate) | -49 |
| Lawrence Park South | 155 | 2 (lower) | 109 | 31 (moderate) | +46 |
| Beechborough-Greenbrook | 61 | 62 (elevated) | 15 | 91 (high) | +46 |
| Milliken | 58 | 64 (elevated) | 13 | 92 (high) | +45 |
| Keelesdale-Eglinton West | 124 | 22 (lower) | 79 | 50 (elevated) | +45 |
| Banbury-Don Mills | 107 | 32 (moderate) | 66 | 59 (elevated) | +41 |
| Markland Wood | 122 | 23 (lower) | 82 | 48 (moderate) | +40 |

## Lowest 10 under CSI

| Neighbourhood | Demo rank | Demo score | CSI rank | CSI score | Change |
|---|---|---|---|---|---|
| Mount Pleasant East | 145 | 8 (lower) | 149 | 6 (lower) | -4 |
| Forest Hill North | 151 | 4 (lower) | 150 | 5 (lower) | +1 |
| Guildwood | 141 | 11 (lower) | 151 | 4 (lower) | -10 |
| Eringate-Centennial-West Deane | 138 | 13 (lower) | 152 | 4 (lower) | -14 |
| Danforth East York | 134 | 15 (lower) | 153 | 3 (lower) | -19 |
| Humber Bay Shores | 136 | 14 (lower) | 154 | 3 (lower) | -18 |
| Avondale | 132 | 17 (lower) | 155 | 2 (lower) | -23 |
| South Eglinton-Davisville | 147 | 7 (lower) | 156 | 1 (lower) | -9 |
| Westminster-Branson | 130 | 18 (lower) | 157 | 1 (lower) | -27 |
| Lambton Baby Point | 158 | 0 (lower) | 158 | 0 (lower) | +0 |

## What changed with the 3-year homicide average (2026-10-01, 01-03-solidify.md)

The first version of this report (scores computed 2026-10-01 16:30 UTC) showed single homicides moving small neighbourhoods a long way. With homicides averaged over 2023–2025:

| Neighbourhood | CSI rank before | CSI rank now | Demo rank |
|---|---|---|---|
| Bayview Woods-Steeles | 63 | 112 | 137 |
| Mount Dennis | 41 | 86 | 98 |
| Yonge-Bay Corridor | 1 | 1 | 2 |
| Mimico-Queensway | 19 | 17 | 1 |

Bridle Path-Sunnybrook-York Mills still ranks higher than under the demo weights. That comes from break-ins, which StatCan weights 8 times a common assault, not from homicides.
