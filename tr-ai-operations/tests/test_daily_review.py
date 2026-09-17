import datetime as dt

import pandas as pd
import pytest

from database import database as db_module
from database.database import init_db, session_scope
from modules.tracking.alert_runner import run_alert_engine_for_records
from modules.tracking.processor import process_file
from services.daily_review import generate_daily_review
from utils.constants import Col


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)
    db_module.reset_engine_for_testing()
    init_db(db_path)
    yield db_path
    db_module.reset_engine_for_testing()


def sample_df(carrier="TN01AB1234", branch="Chennai", remarks=""):
    return pd.DataFrame(
        [
            {
                Col.CARRIER_NUMBER: carrier,
                Col.VEHICLE_CATEGORY: "Car Carrier",
                Col.VEHICLE_STATUS: "In Transit",
                Col.GPS_WORKING: "No",  # deliberately triggers a GPS alert
                Col.ENTERED_BY_BRANCH: branch,
                Col.REMARKS: remarks,
                Col.DAYS_AT_LOCATION: 1,
            }
        ]
    )


def test_review_reports_no_data_available_when_nothing_uploaded(temp_db):
    with session_scope(temp_db) as session:
        review = generate_daily_review(session, dt.date.today())

    assert review["report_status"]["branch_reports_received"] == "Data not available."
    assert review["critical_issues"] == []
    assert review["pod_status"].startswith("Coming Soon")
    assert review["accounts_status"].startswith("Coming Soon")
    assert review["hr_status"].startswith("Coming Soon")


def test_review_summarizes_todays_uploads_and_alerts(temp_db):
    with session_scope(temp_db) as session:
        process_file(session, "chennai.xlsx", sample_df())
        from database.models import TrackingRecord

        records = session.query(TrackingRecord).all()
        run_alert_engine_for_records(session, records)

    with session_scope(temp_db) as session:
        review = generate_daily_review(session, dt.date.today())

    assert review["report_status"]["branch_reports_received"] == 1
    assert review["report_status"]["vehicles_processed"] == 1
    assert review["operational_summary"]["gps_issues"] >= 1
    assert len(review["branch_summary"]) == 1
    assert review["branch_summary"][0]["branch"] == "Chennai"


def test_review_never_fabricates_accident_when_none_reported(temp_db):
    with session_scope(temp_db) as session:
        process_file(session, "chennai.xlsx", sample_df())
        from database.models import TrackingRecord

        records = session.query(TrackingRecord).all()
        run_alert_engine_for_records(session, records)

    with session_scope(temp_db) as session:
        review = generate_daily_review(session, dt.date.today())

    assert not any("Accident" in issue for issue in review["critical_issues"])
