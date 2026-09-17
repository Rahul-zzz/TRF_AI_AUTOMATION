import pandas as pd

from modules.tracking.validation import summarize_issues, validate_dataframe
from utils.constants import Col, Severity


def make_df(**overrides):
    base = {
        Col.CARRIER_NUMBER: "TN01AB1234",
        Col.VEHICLE_CATEGORY: "Car Carrier",
        Col.VEHICLE_STATUS: "In Transit",
        Col.GPS_WORKING: "Yes",
        Col.ENTERED_BY_BRANCH: "Chennai",
        Col.DAYS_AT_LOCATION: 2,
        Col.LOAD_DATE: "2026-09-01",
    }
    base.update(overrides)
    return pd.DataFrame([base])


def test_missing_carrier_number_is_error():
    df = make_df(**{Col.CARRIER_NUMBER: ""})
    issues = validate_dataframe(df, [])
    assert any(i.severity == Severity.ERROR and i.column == Col.CARRIER_NUMBER for i in issues)


def test_invalid_date_is_error():
    df = make_df(**{Col.LOAD_DATE: "not-a-date"})
    issues = validate_dataframe(df, [])
    assert any(i.severity == Severity.ERROR and i.column == Col.LOAD_DATE for i in issues)


def test_negative_numeric_is_error():
    df = make_df(**{Col.DAYS_AT_LOCATION: -3})
    issues = validate_dataframe(df, [])
    assert any(i.severity == Severity.ERROR and i.column == Col.DAYS_AT_LOCATION for i in issues)


def test_unknown_gps_value_is_warning():
    df = make_df(**{Col.GPS_WORKING: "Maybe"})
    issues = validate_dataframe(df, [])
    assert any(i.severity == Severity.WARNING and i.column == Col.GPS_WORKING for i in issues)


def test_clean_row_has_no_errors():
    df = make_df()
    issues = validate_dataframe(df, [])
    summary = summarize_issues(issues)
    assert summary["errors"] == 0


def test_missing_required_short_circuits_row_validation():
    df = make_df()
    issues = validate_dataframe(df, [Col.CARRIER_NUMBER])
    assert len(issues) == 1
    assert issues[0].severity == Severity.ERROR
