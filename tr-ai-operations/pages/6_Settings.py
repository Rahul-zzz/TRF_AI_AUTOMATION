import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import dataclasses

import pandas as pd
import streamlit as st

from config.settings import SETTINGS
from utils.constants import KNOWN_BRANCHES, KNOWN_GPS_VALUES, KNOWN_VEHICLE_STATUSES

st.set_page_config(page_title="Settings — TR AI Operations Platform", page_icon="⚙️", layout="wide")

st.title("⚙️ Settings — Prototype Configuration")
st.warning(
    "All values below are **PROTOTYPE THRESHOLDS**, not official TR Finished Vehicles "
    "Logistics business rules. They must be validated by operations staff before being "
    "treated as policy."
)

st.subheader("Alert Thresholds")
thresholds_dict = dataclasses.asdict(SETTINGS.thresholds)
thresholds_dict.pop("is_prototype", None)
st.table(pd.DataFrame(thresholds_dict.items(), columns=["Setting", "Value (days)"]))
st.caption(
    "To change these without editing code, set the matching environment variable "
    "(same name as the setting) before launching the app — see .env.example."
)

st.subheader("Known Branches")
st.write(", ".join(KNOWN_BRANCHES))
st.caption("Branches encountered in uploaded files that aren't in this list are still accepted and created automatically — this list is only used as a fallback suggestion in manual branch selection.")

st.subheader("Known Vehicle Statuses")
st.write(", ".join(KNOWN_VEHICLE_STATUSES))

st.subheader("Known GPS Values")
st.write(", ".join(KNOWN_GPS_VALUES))

st.subheader("Database")
st.code(SETTINGS.database_path)

st.divider()
st.caption(
    "This page is read-only in Version 0.1 (thresholds are edited via environment "
    "variables or config/settings.py). An editable settings UI backed by the database "
    "is a reasonable next development step."
)
