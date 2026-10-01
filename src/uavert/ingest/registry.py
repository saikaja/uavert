"""Every data source: name, licence and attribution, as shown in the app."""

from dataclasses import dataclass

TPS_PORTAL = "https://data.tps.ca/"
TPS_LICENCE = "Toronto Police Service open data terms of use (data.tps.ca); data is preliminary and locations are offset to the nearest intersection"
TPS_ATTRIBUTION = "Source: Toronto Police Service Public Safety Data Portal"


@dataclass(frozen=True)
class SourceInfo:
    key: str
    name: str
    url: str
    licence: str
    attribution: str


SOURCES = [
    SourceInfo("statcan_csi", "Statistics Canada Crime Severity Index weights (2009 published table)",
               "https://www150.statcan.gc.ca/n1/pub/85-004-x/2009001/t001-eng.htm",
               "Statistics Canada Open Licence", "Source: Statistics Canada, Measuring Crime in Canada (85-004-X)"),
    SourceInfo("tps_ncr", "Toronto Police Neighbourhood Crime Rates and boundaries", TPS_PORTAL, TPS_LICENCE, TPS_ATTRIBUTION),
    SourceInfo("tps_mci", "Toronto Police Major Crime Indicators", TPS_PORTAL, TPS_LICENCE, TPS_ATTRIBUTION),
    SourceInfo("tps_shootings", "Toronto Police Shootings and Firearm Discharges", TPS_PORTAL, TPS_LICENCE, TPS_ATTRIBUTION),
    SourceInfo("tps_homicides", "Toronto Police Homicides", TPS_PORTAL, TPS_LICENCE, TPS_ATTRIBUTION),
    SourceInfo("toronto_tmc", "City of Toronto intersection traffic counts (pedestrians, cyclists, vehicles)",
               "https://open.toronto.ca/dataset/traffic-volumes-at-intersections-for-all-modes/",
               "Open Government Licence - Toronto (City of Toronto Open Data portal); the dataset page lists the licence as not specified, confirm before public launch",
               "Contains information licensed under the Open Government Licence - Toronto"),
    SourceInfo("eccc_aqhi", "Environment Canada Air Quality Health Index (observations)",
               "https://api.weather.gc.ca/collections/aqhi-observations-realtime",
               "Environment and Climate Change Canada Data Servers End-use Licence",
               "Data from Environment and Climate Change Canada (MSC GeoMet)"),
    SourceInfo("eccc_alerts", "Environment Canada weather alerts",
               "https://api.weather.gc.ca/collections/weather-alerts",
               "Environment and Climate Change Canada Data Servers End-use Licence",
               "Data from Environment and Climate Change Canada (MSC GeoMet)"),
    SourceInfo("news_cbc", "CBC News Toronto (RSS)", "https://www.cbc.ca/news/canada/toronto",
               "CBC RSS feed terms: personal, non-commercial use. Headlines and links only; needs permission or a licensed feed before public launch",
               "CBC News"),
    SourceInfo("news_gdelt", "The GDELT Project (DOC API)", "https://www.gdeltproject.org/",
               "GDELT Project terms of use (free, with attribution)", "The GDELT Project"),
]
SOURCE_KEYS = {s.key for s in SOURCES}
