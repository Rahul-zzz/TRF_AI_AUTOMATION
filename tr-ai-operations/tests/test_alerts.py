import datetime as dt

from config.settings import AlertThresholds
from modules.tracking.alerts import evaluate_record
from utils.constants import AlertCategory, Col, Priority

THRESHOLDS = AlertThresholds()
TODAY = dt.date(2026, 9, 16)


def base_record(**overrides):
    record = {
        Col.CARRIER_NUMBER: "TN01AB1234",
        Col.VEHICLE_STATUS: "In Transit",
        Col.GPS_WORKING: "Yes",
        Col.REMARKS: "No issues reported",
        Col.RUNNING_ROUTE: "Chennai-Delhi",
        Col.FROM_CITY: "Chennai",
        Col.TO_CITY_1: "Delhi",
        Col.DAYS_AT_LOCATION: 1,
        Col.DAYS_IN_TRANSIT: 1,
        Col.EXPECTED_UNLOADING_DATE: None,
        Col.ACTUAL_UNLOADING_DATE: None,
        Col.DATE_OF_CURRENT_STATUS: TODAY,
    }
    record.update(overrides)
    return record


def categories(alerts):
    return {a.category for a in alerts}


def test_normal_vehicle_has_no_critical_alert():
    alerts = evaluate_record(base_record(), THRESHOLDS, TODAY)
    assert all(a.priority != Priority.CRITICAL for a in alerts)


def test_gps_not_working_triggers_high_alert():
    alerts = evaluate_record(base_record(**{Col.GPS_WORKING: "No"}), THRESHOLDS, TODAY)
    gps_alerts = [a for a in alerts if a.category == AlertCategory.GPS_ISSUE]
    assert len(gps_alerts) == 1
    assert gps_alerts[0].priority == Priority.HIGH


def test_accident_keyword_triggers_critical_alert():
    record = base_record(**{Col.REMARKS: "Accident reported near Chennai."})
    alerts = evaluate_record(record, THRESHOLDS, TODAY)
    accident_alerts = [a for a in alerts if a.category == AlertCategory.ACCIDENT]
    assert len(accident_alerts) == 1
    assert accident_alerts[0].priority == Priority.CRITICAL


def test_unloading_delay_detected_when_expected_date_passed():
    record = base_record(**{Col.EXPECTED_UNLOADING_DATE: TODAY - dt.timedelta(days=5), Col.ACTUAL_UNLOADING_DATE: None})
    alerts = evaluate_record(record, THRESHOLDS, TODAY)
    delay_alerts = [a for a in alerts if a.category == AlertCategory.UNLOADING_DELAY]
    assert len(delay_alerts) == 1
    assert delay_alerts[0].priority == Priority.CRITICAL  # 5 days >= CRITICAL threshold (4)


def test_high_days_at_location_triggers_alert():
    record = base_record(**{Col.DAYS_AT_LOCATION: 9})
    alerts = evaluate_record(record, THRESHOLDS, TODAY)
    dal_alerts = [a for a in alerts if a.category == AlertCategory.EXCESSIVE_DAYS_AT_LOCATION]
    assert len(dal_alerts) == 1
    assert dal_alerts[0].priority == Priority.CRITICAL


def test_duplicate_upload_does_not_crash_priority_classification():
    record = base_record(**{Col.DAYS_IN_TRANSIT: 10})
    alerts = evaluate_record(record, THRESHOLDS, TODAY)
    transit_alerts = [a for a in alerts if a.category == AlertCategory.TRANSIT_DELAY]
    assert len(transit_alerts) == 1
    assert transit_alerts[0].priority == Priority.HIGH


def test_stale_status_date_triggers_tracking_inactivity():
    record = base_record(**{Col.DATE_OF_CURRENT_STATUS: TODAY - dt.timedelta(days=6)})
    alerts = evaluate_record(record, THRESHOLDS, TODAY)
    inactivity_alerts = [a for a in alerts if a.category == AlertCategory.TRACKING_INACTIVITY]
    assert len(inactivity_alerts) == 1
    assert inactivity_alerts[0].priority == Priority.CRITICAL
