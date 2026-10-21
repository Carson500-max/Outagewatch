#!/usr/bin/env python3
"""
SDG&E Outage Watch
Sends phone alerts via ntfy when an unplanned SDG&E outage starts,
when it becomes big, and when power comes back.
"""

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

# ---------------- SETTINGS ----------------
BIG_CUSTOMERS = 200          # big if this many customers out, OR
BIG_CUSTOMER_HOURS = 300     # customers x hours out reaches this
RESTORE_MIN_CUSTOMERS = 1    # raise to 10 to skip single-house restores
RESTORE_MIN_HOURS = 0.5      # skip blips shorter than this
OUTAGE_TYPES = {"Not Planned", "Unknown"}
COUNTIES = {"SAN DIEGO"}     # add "ORANGE" for south OC; empty set = all
QUIET_START_HOUR = 21        # 9 PM - alerts arrive silently overnight
QUIET_END_HOUR = 7           # 7 AM
MISSES_BEFORE_RESTORED = 2
# ------------------------------------------

FEED = ("https://services.arcgis.com/BLN4oKB0N1YSgvY8/ArcGIS/rest/services/"
        "Power_Outages_(View)/FeatureServer/0/query")
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
STATE_FILE = os.environ.get("STATE_FILE", "state.json")
PACIFIC = ZoneInfo("America/Los_Angeles")
UA = "sdge-outage-watch/1.0 (personal canvassing alerts)"


def fetch_outages():
    outages, offset = {}, 0
    while True:
        params = {
            "where": "UtilityCompany='SDGE'",
            "outFields": "IncidentId,StartDate,EstimatedRestoreDate,Cause,"
                         "ImpactedCustomers,County,OutageStatus,OutageType",
            "outSR": "4326",
            "resultOffset": str(offset),
            "resultRecordCount": "1000",
            "f": "json",
        }
        url = FEED + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        if "error" in data:
            raise RuntimeError(f"Feed error: {data['error']}")
        feats = data.get("features", [])
        for f in feats:
            outages.update(parse_feature(f))
        if not data.get("exceededTransferLimit") or not feats:
            break
        offset += len(feats)
    return outages


def parse_feature(f):
    a = f.get("attributes", {})
    g = f.get("geometry") or {}
    iid = str
