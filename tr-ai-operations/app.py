"""
TR AI Operations Platform — Home / Dashboard entry point.

Run with: streamlit run app.py
"""

import sys
from pathlib import Path

# Ensure project root is importable regardless of the working directory
# Streamlit is launched from.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

from config.settings import SETTINGS
from database.database import init_db, session_scope
from modules.accounts.placeholder import get_status as accounts_status
from modules.hr.placeholder import get_status as hr_status
from modules.pod.placeholder import get_status as pod_status
from modules.tracking.analytics import compute_kpis

st.set_page_config(page_title=SETTINGS.app_name, page_icon="🚛", layout="wide")

init_db()


def render_platform_status():
    st.subheader("Platform Status")
    cols = st.columns(4)
    cols[0].success("🚛 Tracking\n\nActive")
    cols[1].info(f"📦 POD\n\n{pod_status()['status']}")
    cols[2].info(f"💰 Accounts\n\n{accounts_status()['status']}")
    cols[3].info(f"👥 HR\n\n{hr_status()['status']}")


def render_tracking_summary():
    st.subheader("Tracking Summary")
    with session_scope() as session:
        kpis = compute_kpis(session)

    if not kpis.get("has_data"):
        st.warning("No tracking data available. Upload a report to begin.")
        st.page_link("pages/1_Tracking.py", label="Go to Tracking →", icon="🚛")
        return

    row1 = st.columns(4)
    row1[0].metric("Total Vehicles", kpis["total_vehicles"])
    row1[1].metric("Normal Vehicles", kpis["normal_vehicles"])
    row1[2].metric("Critical Alerts", kpis["critical_alerts"])
    row1[3].metric("High Alerts", kpis["high_alerts"])

    row2 = st.columns(4)
    row2[0].metric("Medium Alerts", kpis["medium_alerts"])
    row2[1].metric("GPS Issues", kpis["gps_issues"])
    row2[2].metric("Delayed Vehicles", kpis["delayed_vehicles"])
    row2[3].metric("Branches Processed", kpis["branches_processed"])


def main():
    st.title(f"🚛 {SETTINGS.app_name}")
    st.caption(SETTINGS.app_subtitle)
    st.caption(SETTINGS.company_name)

    render_platform_status()
    st.divider()
    render_tracking_summary()

    st.divider()
    st.caption(
        "This is a local prototype. Alert priorities and thresholds shown throughout "
        "this application are PROTOTYPE RULES pending validation by TR operations staff — "
        "see the Settings page."
    )


if __name__ == "__main__":
    main()
else:
    main()
