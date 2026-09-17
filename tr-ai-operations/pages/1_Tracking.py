import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import datetime as dt

import pandas as pd
import plotly.express as px
import streamlit as st

from config.settings import SETTINGS
from database.database import init_db, session_scope
from database.operations import all_branches
from modules.tracking import analytics
from modules.tracking.alert_runner import run_alert_engine_for_records
from modules.tracking.column_mapping import normalize_columns
from modules.tracking.processor import process_multiple_files, read_excel_file
from modules.tracking.reports import dataframe_to_csv_bytes, dataframe_to_excel_bytes
from modules.tracking.synthetic_data import generate_synthetic_tracking_dataframe, to_display_excel_bytes
from modules.tracking.validation import issues_to_dataframe, summarize_issues
from utils.constants import SYNTHETIC_DATA_LABEL, Priority

st.set_page_config(page_title="Tracking — TR AI Operations Platform", page_icon="🚛", layout="wide")
init_db()

st.title("🚛 Tracking")

tabs = st.tabs(
    [
        "🧬 Synthetic Demo Data",
        "📤 Upload & Process",
        "📊 Dashboard",
        "🚨 Alerts",
        "🔍 Vehicle Search",
        "🏢 Branch Analytics",
        "🧪 Data Quality",
    ]
)

# ---------------------------------------------------------------------------
# Synthetic Demo Data
# ---------------------------------------------------------------------------
with tabs[0]:
    st.warning(SYNTHETIC_DATA_LABEL)
    st.write(
        "Generate a realistic sample Tracking report to test the full pipeline "
        "before real branch files are available. Synthetic uploads are flagged "
        "in the database and are never mixed with real data."
    )

    demo_mode = st.radio(
        "Demo type",
        ["Single file (one branch)", "Multi-branch (one file per branch, for testing consolidation)"],
        horizontal=True,
    )

    if demo_mode == "Single file (one branch)":
        num_vehicles = st.slider("Number of synthetic vehicles", 50, 400, 220, step=10)
        seed = st.number_input("Random seed (optional, for reproducibility)", min_value=0, value=42)

        if st.button("Generate Demo Tracking Data", type="primary"):
            df = generate_synthetic_tracking_dataframe(num_vehicles=num_vehicles, seed=int(seed), branch="Chennai")
            st.session_state["synthetic_df"] = df
            st.success(f"Generated {len(df)} synthetic rows for branch 'Chennai'.")

        if "synthetic_df" in st.session_state:
            df = st.session_state["synthetic_df"]
            st.dataframe(df.head(20), use_container_width=True)
            excel_bytes = to_display_excel_bytes(df)
            st.download_button(
                "⬇️ Download synthetic_tracking_demo.xlsx",
                data=excel_bytes,
                file_name="synthetic_tracking_demo.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            st.caption("Download this file, then use the Upload & Process tab to feed it through the real pipeline — exactly like a branch report.")
    else:
        from modules.tracking.synthetic_data import generate_synthetic_multi_branch_files

        vehicles_per_branch = st.slider("Vehicles per branch", 10, 60, 25, step=5)
        seed2 = st.number_input("Random seed (optional)", min_value=0, value=7, key="multi_seed")

        if st.button("Generate Multi-Branch Demo Files", type="primary"):
            files = generate_synthetic_multi_branch_files(vehicles_per_branch=vehicles_per_branch, seed=int(seed2))
            st.session_state["synthetic_multi_files"] = files
            st.success(f"Generated {len(files)} branch files, {vehicles_per_branch} vehicles each.")

        if "synthetic_multi_files" in st.session_state:
            import io
            import zipfile

            files = st.session_state["synthetic_multi_files"]
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for branch_name, df in files.items():
                    zf.writestr(f"{branch_name}.xlsx", to_display_excel_bytes(df))
            st.download_button(
                "⬇️ Download all branch files (.zip)",
                data=zip_buffer.getvalue(),
                file_name="synthetic_multi_branch_demo.zip",
                mime="application/zip",
            )
            st.caption("Unzip and upload the individual .xlsx files in the Upload & Process tab to test multi-branch consolidation.")
            for branch_name, df in files.items():
                with st.expander(f"Preview: {branch_name}.xlsx ({len(df)} rows)"):
                    st.dataframe(df.head(10), use_container_width=True)

# ---------------------------------------------------------------------------
# Upload & Process
# ---------------------------------------------------------------------------
with tabs[1]:
    st.write("Upload one or more branch Tracking Excel files (`.xlsx`).")
    uploaded_files = st.file_uploader("Tracking report(s)", type=["xlsx"], accept_multiple_files=True)

    is_synthetic_upload = st.checkbox(
        "These file(s) are synthetic/demo data (not a real company report)", value=True
    )

    manual_branches: dict[str, str] = {}

    if uploaded_files:
        st.write("#### Files to process")
        for f in uploaded_files:
            try:
                preview_df = read_excel_file(f)
                f.seek(0)
                mapping = normalize_columns(preview_df)
                detected_branch = None
                from modules.tracking.processor import detect_branch_name

                detected_branch = detect_branch_name(mapping.dataframe)
            except Exception as exc:
                st.error(f"**{f.name}** — could not read file: {exc}")
                continue

            with st.expander(f"📄 {f.name} — {len(preview_df)} rows, {len(preview_df.columns)} columns", expanded=True):
                if mapping.missing_required:
                    st.error(f"Missing required columns: {', '.join(mapping.missing_required)}")
                if mapping.unmapped_columns:
                    st.info(f"Unrecognized columns kept as-is (not mapped): {', '.join(mapping.unmapped_columns)}")
                if detected_branch:
                    st.success(f"Detected branch: **{detected_branch}**")
                else:
                    st.warning("Branch could not be auto-detected — please select manually.")
                    with session_scope() as s:
                        existing_branches = [b.name for b in all_branches(s)]
                    from utils.constants import KNOWN_BRANCHES

                    options = ["-- Select branch --"] + sorted(set(existing_branches) | set(KNOWN_BRANCHES))
                    choice = st.selectbox(f"Branch for {f.name}", options, key=f"branch_select_{f.name}")
                    if choice and choice != "-- Select branch --":
                        manual_branches[f.name] = choice

        if st.button("Process Files", type="primary"):
            files_payload = []
            for f in uploaded_files:
                f.seek(0)
                df = read_excel_file(f)
                files_payload.append((f.name, df))

            with session_scope() as session:
                results = process_multiple_files(
                    session, files_payload, manual_branch_overrides=manual_branches, is_synthetic=is_synthetic_upload
                )
                # Run the alert engine over all records (re-evaluates every
                # rule against the full historical set; cheap at MVP scale).
                from database.models import TrackingRecord

                all_records = session.query(TrackingRecord).all()
                created_alerts = run_alert_engine_for_records(session, all_records)

            st.success(f"Processing complete. {created_alerts} alert(s) evaluated/created across all records.")

            for r in results:
                status_icon = {"SUCCESS": "✅", "PARTIAL": "⚠️", "FAILED": "❌"}.get(r.status, "❓")
                st.write(f"{status_icon} **{r.filename}** — branch: {r.detected_branch or 'N/A'} "
                         f"({r.branch_confidence}) — inserted {r.inserted_rows}/{r.total_rows} rows"
                         f"{f', {r.possible_duplicates} possible duplicate(s)' if r.possible_duplicates else ''}")
                if r.error:
                    st.error(r.error)
                if r.issues:
                    issues_df = issues_to_dataframe(r.issues)
                    summary = summarize_issues(r.issues)
                    st.caption(f"Validation: {summary['errors']} error(s), {summary['warnings']} warning(s), {summary['info']} info")
                    with st.expander(f"View validation details for {r.filename}"):
                        st.dataframe(issues_df, use_container_width=True)
    else:
        st.info("No files uploaded yet. Use the Synthetic Demo Data tab to generate a test file if you don't have a real report handy.")

# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
with tabs[2]:
    with session_scope() as session:
        kpis = analytics.compute_kpis(session)

        if not kpis.get("has_data"):
            st.warning("No tracking data available. Upload a report to begin.")
        else:
            row1 = st.columns(4)
            row1[0].metric("Total Vehicles", kpis["total_vehicles"])
            row1[1].metric("Normal Vehicles", kpis["normal_vehicles"])
            row1[2].metric("Critical Alerts", kpis["critical_alerts"])
            row1[3].metric("High Alerts", kpis["high_alerts"])
            row2 = st.columns(4)
            row2[0].metric("Medium Alerts", kpis["medium_alerts"])
            row2[1].metric("GPS Issues", kpis["gps_issues"])
            row2[2].metric("Vehicles in Transit", kpis["in_transit"])
            row2[3].metric("Delayed Vehicles", kpis["delayed_vehicles"])

            st.divider()

            colA, colB = st.columns(2)
            with colA:
                st.plotly_chart(px.pie(analytics.vehicle_status_distribution(session), names="status", values="count", title="Vehicle Status Distribution"), use_container_width=True)
                st.plotly_chart(px.bar(analytics.alerts_by_category(session), x="category", y="count", title="Alerts by Category"), use_container_width=True)
                st.plotly_chart(px.bar(analytics.vehicles_by_branch(session), x="branch", y="count", title="Vehicle Count by Branch"), use_container_width=True)
            with colB:
                priority_df = analytics.alerts_by_priority(session)
                st.plotly_chart(px.bar(priority_df, x="priority", y="count", title="Alerts by Priority", color="priority"), use_container_width=True)
                st.plotly_chart(px.bar(analytics.alerts_by_branch(session), x="branch", y="count", title="Alerts by Branch"), use_container_width=True)
                st.plotly_chart(px.pie(analytics.gps_status_distribution(session), names="gps_working", values="count", title="GPS Status"), use_container_width=True)

            dal = analytics.days_at_location_distribution(session)
            dit = analytics.days_in_transit_distribution(session)
            colC, colD = st.columns(2)
            if not dal.empty:
                colC.plotly_chart(px.histogram(dal, x="days_at_location", title="Days at Location Distribution"), use_container_width=True)
            if not dit.empty:
                colD.plotly_chart(px.histogram(dit, x="days_in_transit", title="Days in Transit Distribution"), use_container_width=True)

# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------
with tabs[3]:
    with session_scope() as session:
        from database.models import Alert, TrackingRecord, Vehicle, Branch

        query = (
            session.query(Alert, TrackingRecord, Vehicle, Branch)
            .join(TrackingRecord, Alert.tracking_record_id == TrackingRecord.id)
            .join(Vehicle, TrackingRecord.vehicle_id == Vehicle.id)
            .outerjoin(Branch, TrackingRecord.branch_id == Branch.id)
            .order_by(Alert.detected_at.desc())
        )
        rows = query.all()

        if not rows:
            st.info("No alerts yet — process a Tracking report to generate alerts.")
        else:
            col1, col2, col3 = st.columns(3)
            priority_filter = col1.multiselect("Priority", [p.value for p in Priority], default=[p.value for p in Priority])
            categories = sorted({a.category for a, *_ in rows})
            category_filter = col2.multiselect("Category", categories, default=categories)
            branches = sorted({b.name for *_, b in rows if b})
            branch_filter = col3.multiselect("Branch", branches, default=branches)

            table_rows = []
            for alert, record, vehicle, branch in rows:
                if alert.priority not in priority_filter:
                    continue
                if alert.category not in category_filter:
                    continue
                if branch and branch.name not in branch_filter:
                    continue
                table_rows.append(
                    {
                        "Alert ID": alert.id,
                        "Date": alert.detected_at.strftime("%Y-%m-%d %H:%M") if alert.detected_at else "",
                        "Vehicle": vehicle.carrier_number,
                        "Branch": branch.name if branch else "Unknown",
                        "Category": alert.category,
                        "Priority": alert.priority,
                        "Description": alert.message,
                        "Resolved": alert.resolved,
                        "Verified": alert.verified_by_human,
                    }
                )
            st.dataframe(pd.DataFrame(table_rows), use_container_width=True, height=450)
            st.caption("Alert priorities/thresholds are PROTOTYPE RULES — see Settings. Historical alerts are never deleted.")

# ---------------------------------------------------------------------------
# Vehicle Search
# ---------------------------------------------------------------------------
with tabs[4]:
    with session_scope() as session:
        col1, col2, col3 = st.columns(3)
        carrier = col1.text_input("Carrier Number")
        branch = col2.text_input("Branch")
        location = col3.text_input("Current Location")
        col4, col5, col6 = st.columns(3)
        status = col4.text_input("Vehicle Status")
        consigner = col5.text_input("Consigner")
        state = col6.text_input("State")

        results = analytics.search_vehicles(
            session,
            carrier_number=carrier,
            branch=branch,
            current_location=location,
            vehicle_status=status,
            consigner=consigner,
            state=state,
        )

        st.write(f"**{len(results)} vehicle(s) found**")
        for r in results[:100]:
            with st.expander(f"{r.vehicle.carrier_number if r.vehicle else 'Unknown'} — {r.vehicle_status or 'Unknown status'} ({r.branch.name if r.branch else 'Unknown branch'})"):
                details = {
                    "Carrier Number": r.vehicle.carrier_number if r.vehicle else None,
                    "Vehicle Category": r.vehicle.vehicle_category if r.vehicle else None,
                    "Running Route": r.running_route,
                    "YTD Grade": r.ytd_grade,
                    "Consigner": r.consigner,
                    "Load Date": r.load_date,
                    "Dispatch Date": r.dispatch_date,
                    "Expected Unloading Date": r.expected_unloading_date,
                    "Actual Unloading Date": r.actual_unloading_date,
                    "Current Location": r.current_location,
                    "State": r.state,
                    "Next Loading Station": r.next_loading_station,
                    "Vehicle Status": r.vehicle_status,
                    "Date of Current Status": r.date_of_current_status,
                    "GPS Working": r.gps_working,
                    "Days at Location": r.days_at_location,
                    "Days in Transit": r.days_in_transit,
                    "Branch": r.branch.name if r.branch else None,
                    "Remarks": r.remarks,
                }
                st.table(pd.DataFrame(details.items(), columns=["Field", "Value"]))
                from database.operations import alerts_for_records

                active_alerts = alerts_for_records(session, [r.id])
                if active_alerts:
                    st.write("**Active Alerts:**")
                    for a in active_alerts:
                        st.write(f"- [{a.priority}] {a.category}: {a.message}")
                else:
                    st.caption("No active alerts for this vehicle.")

# ---------------------------------------------------------------------------
# Branch Analytics
# ---------------------------------------------------------------------------
with tabs[5]:
    with session_scope() as session:
        summary_df = analytics.branch_summary(session)
        if summary_df.empty:
            st.info("No data available yet.")
        else:
            st.dataframe(summary_df, use_container_width=True)
            st.plotly_chart(px.bar(summary_df, x="branch", y=["total_vehicles", "critical_alerts", "high_alerts"], barmode="group", title="Branch Comparison"), use_container_width=True)
            st.caption("Branch metrics are shown as raw counts. Rankings are not implied — sample sizes vary by branch.")
            st.download_button(
                "⬇️ Export branch summary (Excel)",
                data=dataframe_to_excel_bytes(summary_df, "Branch Summary"),
                file_name="branch_summary.xlsx",
            )

# ---------------------------------------------------------------------------
# Data Quality
# ---------------------------------------------------------------------------
with tabs[6]:
    with session_scope() as session:
        from database.models import TrackingRecord

        records = session.query(TrackingRecord).all()
        if not records:
            st.info("No data available yet.")
        else:
            missing_branch = sum(1 for r in records if not r.branch_id)
            missing_gps = sum(1 for r in records if not r.gps_working)
            missing_status_date = sum(1 for r in records if not r.date_of_current_status)
            invalid_gps = sum(1 for r in records if r.gps_working and r.gps_working.strip().title() not in {"Yes", "No"})

            cols = st.columns(4)
            cols[0].metric("Records Missing Branch", missing_branch)
            cols[1].metric("Records Missing GPS Value", missing_gps)
            cols[2].metric("Records Missing Status Date", missing_status_date)
            cols[3].metric("Invalid GPS Values", invalid_gps)
            st.caption("These counts reflect all historical records currently in the database, not just the latest upload.")
