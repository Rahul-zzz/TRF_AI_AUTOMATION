import datetime as dt

import pandas as pd
import pytest

from database import database as db_module
from database.database import init_db, session_scope
from database.models import TrackingRecord, Vehicle
from modules.tracking.processor import process_file
from utils.constants import Col


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)
    db_module.reset_engine_for_testing()
    init_db(db_path)
    yield db_path
    db_module.reset_engine_for_testing()


def sample_df(carrier="TN01AB1234", branch="Chennai", load_date="2026-09-01"):
    return pd.DataFrame(
        [
            {
                Col.CARRIER_NUMBER: carrier,
                Col.VEHICLE_CATEGORY: "Car Carrier",
                Col.VEHICLE_STATUS: "In Transit",
                Col.GPS_WORKING: "Yes",
                Col.ENTERED_BY_BRANCH: branch,
                Col.LOAD_DATE: load_date,
                Col.DAYS_AT_LOCATION: 1,
            }
        ]
    )


def test_insert_creates_vehicle_and_record(temp_db):
    with session_scope(temp_db) as session:
        result = process_file(session, "test.xlsx", sample_df())
        assert result.status == "SUCCESS"
        assert result.inserted_rows == 1

    with session_scope(temp_db) as session:
        vehicles = session.query(Vehicle).all()
        records = session.query(TrackingRecord).all()
        assert len(vehicles) == 1
        assert len(records) == 1
        assert vehicles[0].carrier_number == "TN01AB1234"


def test_historical_records_are_never_deleted_on_new_upload(temp_db):
    with session_scope(temp_db) as session:
        process_file(session, "day1.xlsx", sample_df(load_date="2026-09-01"))

    with session_scope(temp_db) as session:
        process_file(session, "day2.xlsx", sample_df(load_date="2026-09-10"))

    with session_scope(temp_db) as session:
        records = session.query(TrackingRecord).all()
        # Same vehicle, two different load dates -> two retained rows.
        assert len(records) == 2


def test_possible_duplicate_is_flagged_not_dropped(temp_db):
    with session_scope(temp_db) as session:
        process_file(session, "day1.xlsx", sample_df(load_date="2026-09-01"))

    with session_scope(temp_db) as session:
        result = process_file(session, "day1_reupload.xlsx", sample_df(load_date="2026-09-01"))
        assert result.possible_duplicates == 1
        assert result.inserted_rows == 1  # inserted anyway, flagged not silently dropped

    with session_scope(temp_db) as session:
        records = session.query(TrackingRecord).all()
        assert len(records) == 2
