# Expanding beyond Toronto: data permissions (notes)

*Checked 2026-10-01. Not a phase document: this records what was found so the GTA expansion can start from it later.*

## Decision
On 2026-10-01 the user first chose "Start York + Durham now", with each region ranked within itself. Claude then checked the data licences and stopped before building, because York prohibits commercial use and Durham publishes no licence. The user agreed: **note the permissions and move on.** No GTA code was written.

## What each police service publishes

| Region | Data found | Licence / terms | Status |
|---|---|---|---|
| **Toronto** (in use) | Incident-level open data (Major Crime Indicators, shootings, homicides, neighbourhood rates) | **Open Government Licence – Ontario**: use "including for commercial purposes", with attribution | ✅ In use. The app shows the exact licence and attribution (commit `cfb0bfb`) |
| **York** (Vaughan, Markham, Richmond Hill, Newmarket, Aurora, Georgina, East Gwillimbury, Whitchurch-Stouffville, King) | `services8.arcgis.com/lYI034SQcOoxRCR7/.../Occurrence/FeatureServer` (year to date, 78,005 records) and `.../Occurrence_2016_to_2019/FeatureServer` (2021–2025, 177,770 records). Fields: offence (`case_type_pubtrans`), `LocationCode` (Business / Residence / Outdoor), `municipality`, `occ_date`, `time_est`, `Shooting`, `hate_crime`; mapped to the nearest intersection | Terms state: "**Any use of the information or data for commercial purposes is strictly prohibited**", and the data "should not be used to make decisions or comparisons regarding the safety or crime levels for a specific area" | ❌ **Needs written permission or a data-sharing agreement** |
| **Durham** (Oshawa, Whitby, Ajax, Pickering, Clarington, Uxbridge, Scugog, Brock) | `services6.arcgis.com/2r8RrIqBhHAeyu7x/...`: separate layers for Assault (17,310), Robbery (1,598), B&E (7,642), Auto Theft (6,854), Theft Over $5,000 (1,482), Firearm Shooting, Drug Violations, Traffic Collision. Fields are close to Toronto's: `event_unique_id`, `offence`, `location_type` (premises), occurrence year/month/day/hour, `municipality`, `neighbourhood`, `lat`/`lon` | **No licence stated** on any data layer; the portal pages carry only Esri's template notice | ⚠️ **Ask for permission or a licence.** The best technical fit, about a day of work once allowed |
| **Peel** (Mississauga, Brampton) | The data behind Peel Police's crime map app: `services.arcgis.com/w0dAT1ctgtKwxvde/.../Experience_gdb/FeatureServer/0` ("Ecrimes", 81,579 records, 36 months). Fields: offence `Description`, `OccType`, date and hour, street, `Municipality`, `Ward` (no premises type) | Not published as open data; no licence | ⚠️ **Ask for permission.** Don't use the app's service without it |
| **Caledon** | Policed by the OPP | No incident data found | ❌ |
| **Halton** (Oakville, Burlington, Milton, Halton Hills) | Annual statistics and a view-only crime map | No downloadable incident data found | ❌ Only a regional baseline from StatCan |

## What to ask the police services
A short request to each of York, Durham and Peel:
1. **What Uavert is:** a location risk-guidance app for Toronto and the GTA, showing sources and dates, never labelling places "safe", with a published fairness check.
2. **The data wanted:** the existing open crime layers (offence, date and time, approximate location, premises type).
3. **The use:** scores per neighbourhood and street block, with attribution, inside a product that will have paid tiers.
4. **The request:** written permission or a data-sharing agreement, and the attribution wording they require.

## Usable now, if GTA coverage is wanted before permissions arrive
- **Statistics Canada police-reported crime by police service:** the Crime Severity Index for each region, published yearly under the Statistics Canada Open Licence (commercial use allowed). Region-level only, with no street detail.
- **Everything except crime:** Environment Canada air quality and alerts, CBC news (with the same personal-use caveat), OpenStreetMap address search and walking routes. These already cover the GTA.
- **Census tracts for areas outside Toronto:** Statistics Canada's 2021 boundaries are queryable at `geo.statcan.gc.ca/geo_wa/rest/services/2021/Cartographic_boundary_files/MapServer/11`: 1,227 tracts in the Toronto metro area (CTUID 535…), 92 in Oshawa's (532…). Rural Durham (Brock, Scugog) has no tracts, so it would use municipalities. The census profile API ([guide](https://www12.statcan.gc.ca/wds-sdw/2021profile-profil2021-eng.cfm)) returned "NoRecordsFound" for the key formats tried; Statistics Canada's census tract CSV download is the fallback.

## Design decisions already made, for when this resumes
- **Rank within each region:** each police service's area is ranked against itself, and the map says so ("compared with the rest of York Region"), because forces record crime differently.
- **Same scoring rules everywhere:** the same offence set and StatCan weights, mapped per force like `data/offence_map.csv`.
- **Foot traffic outside Toronto:** needs each region's own counts, or a fallback such as the city median or population density.
