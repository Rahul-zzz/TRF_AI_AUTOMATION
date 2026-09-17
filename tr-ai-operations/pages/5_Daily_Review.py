import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import datetime as dt

import pandas as pd
import streamlit as st

from database.database import init_db, session_scope
from modules.tracking.reports import daily_review_to_pdf_bytes, dataframe_to_csv_bytes
from services.daily_review import generate_daily_review

st.set_page_config(page_title="Daily Review — TR AI Operations Platform", page_icon="📋", layout="wide")
init_db()

st.title("📋 Daily Review")
st.caption(
    "TR DAILY TRACKING REVIEW. Only Tracking data is real in this version — "
    "POD, Accounts and HR sections below are explicit placeholders, never fabricated."
)

selected_date = st.date_input("Review date", value=dt.date.today())

if st.button("Generate Daily Review", type="primary"):
    with session_scope() as session:
        review = generate_daily_review(session, selected_date)
    st.session_state["daily_review"] = review

if "daily_review" in st.session_state:
    review = st.session_state["daily_review"]

    st.header(f"TR DAILY TRACKING REVIEW — {review['review_date']}")

    st.subheader("Report Status")
    st.table(pd.DataFrame(review["report_status"].items(), columns=["Metric", "Value"]))

    st.subheader("Operational Summary")
    st.table(pd.DataFrame(review["operational_summary"].items(), columns=["Metric", "Value"]))

    st.subheader("Critical Issues")
    if review["critical_issues"]:
        for item in review["critical_issues"]:
            st.error(item)
    else:
        st.write("None.")

    st.subheader("High Priority Issues")
    if review["high_priority_issues"]:
        for item in review["high_priority_issues"]:
            st.warning(item)
    else:
        st.write("None.")

    st.subheader("Branch Summary")
    if review["branch_summary"]:
        st.dataframe(pd.DataFrame(review["branch_summary"]), use_container_width=True)
    else:
        st.write("Data not available.")

    st.subheader("Recommended Follow-up")
    for item in review["recommended_follow_up"]:
        st.write(f"- {item}")

    st.subheader("Other Departments")
    st.write(f"POD: {review['pod_status']}")
    st.write(f"Accounts: {review['accounts_status']}")
    st.write(f"HR: {review['hr_status']}")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        try:
            pdf_bytes = daily_review_to_pdf_bytes(review)
            st.download_button("⬇️ Export as PDF", data=pdf_bytes, file_name=f"daily_review_{review['review_date']}.pdf", mime="application/pdf")
        except Exception as exc:
            st.caption(f"PDF export unavailable: {exc}")
    with col2:
        import json

        st.download_button(
            "⬇️ Export as JSON",
            data=json.dumps(review, indent=2, default=str).encode("utf-8"),
            file_name=f"daily_review_{review['review_date']}.json",
            mime="application/json",
        )
else:
    st.info("Select a date and click 'Generate Daily Review'.")
