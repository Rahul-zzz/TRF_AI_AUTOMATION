"""
Rule-based alert engine.

Every rule here is deliberately simple and explainable: given specific
field values, produce a specific alert with a specific priority. No LLM
is involved in deciding operational criticality — see services/ai_service.py
for where a future assistant may *explain* an alert in plain language,
which is a different thing from *deciding* one.

All numeric thresholds come from config.settings.SETTINGS.thresholds and
are explicitly labeled PROTOTYPE THRESHOLDS pending validation by TR staff.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Optional

from config.settings import AlertThresholds
from utils.constants import ACCIDENT_KEYWORDS, AlertCategory, Col, Priority


@dataclass
class DetectedAlert:
    category: AlertCategory
    priority: Priority
    message: str
    rule_name: str


def _text_contains_keyword(text: Optional[str], keywords: list[str]) -> Optional[str]:
    if not text:
        return None
    lowered = text.lower()
    for kw in keywords:
        if kw in lowered:
            return kw
    return None


def detect_accident(record: dict) -> Optional[DetectedAlert]:
    remarks_hit = _text_contains_keyword(record.get(Col.REMARKS), ACCIDENT_KEYWORDS)
    status_hit = _text_contains_keyword(record.get(Col.VEHICLE_STATUS), ACCIDENT_KEYWORDS)
    hit = remarks_hit or status_hit
    if not hit:
        return None
    return DetectedAlert(
        category=AlertCategory.ACCIDENT,
        priority=Priority.CRITICAL,
        message=f"Possible Accident Detected (keyword '{hit}' found) — Human Verification Required.",
        rule_name="accident_keyword_match",
    )


def detect_gps_issue(record: dict) -> Optional[DetectedAlert]:
    gps = record.get(Col.GPS_WORKING)
    if gps and str(gps).strip().title() == "No":
        return DetectedAlert(
            category=AlertCategory.GPS_ISSUE,
            priority=Priority.HIGH,
            message="GPS Working = No.",
            rule_name="gps_not_working",
        )
    return None


def detect_unloading_delay(record: dict, thresholds: AlertThresholds, today: dt.date) -> Optional[DetectedAlert]:
    expected = record.get(Col.EXPECTED_UNLOADING_DATE)
    actual = record.get(Col.ACTUAL_UNLOADING_DATE)
    if not expected or actual:
        return None
    overdue_days = (today - expected).days
    if overdue_days < thresholds.UNLOADING_DELAY_HIGH:
        return None
    priority = Priority.CRITICAL if overdue_days >= thresholds.UNLOADING_DELAY_CRITICAL else Priority.HIGH
    return DetectedAlert(
        category=AlertCategory.UNLOADING_DELAY,
        priority=priority,
        message=(
            f"Expected Unloading Date was {expected.isoformat()} ({overdue_days} day(s) ago) "
            f"and no Actual Unloading Date is recorded. [Prototype threshold: {thresholds.UNLOADING_DELAY_HIGH}d]"
        ),
        rule_name="unloading_delay",
    )


def detect_excessive_days_at_location(record: dict, thresholds: AlertThresholds) -> Optional[DetectedAlert]:
    days = record.get(Col.DAYS_AT_LOCATION)
    if days is None:
        return None
    if days >= thresholds.DAYS_AT_LOCATION_CRITICAL:
        priority = Priority.CRITICAL
    elif days >= thresholds.DAYS_AT_LOCATION_HIGH:
        priority = Priority.HIGH
    elif days >= thresholds.DAYS_AT_LOCATION_WARNING:
        priority = Priority.MEDIUM
    else:
        return None
    return DetectedAlert(
        category=AlertCategory.EXCESSIVE_DAYS_AT_LOCATION,
        priority=priority,
        message=(
            f"Vehicle has been at its current location for {days} day(s). "
            f"[Prototype thresholds — warning={thresholds.DAYS_AT_LOCATION_WARNING}d, "
            f"high={thresholds.DAYS_AT_LOCATION_HIGH}d, critical={thresholds.DAYS_AT_LOCATION_CRITICAL}d]"
        ),
        rule_name="excessive_days_at_location",
    )


def detect_transit_delay(record: dict, thresholds: AlertThresholds) -> Optional[DetectedAlert]:
    days = record.get(Col.DAYS_IN_TRANSIT)
    if days is None:
        return None
    if days >= thresholds.DAYS_IN_TRANSIT_HIGH:
        priority = Priority.HIGH
    elif days >= thresholds.DAYS_IN_TRANSIT_WARNING:
        priority = Priority.MEDIUM
    else:
        return None
    return DetectedAlert(
        category=AlertCategory.TRANSIT_DELAY,
        priority=priority,
        message=(
            f"Vehicle has been in transit for {days} day(s). "
            f"[Prototype thresholds — warning={thresholds.DAYS_IN_TRANSIT_WARNING}d, high={thresholds.DAYS_IN_TRANSIT_HIGH}d]"
        ),
        rule_name="transit_delay",
    )


def detect_tracking_inactivity(record: dict, thresholds: AlertThresholds, today: dt.date) -> Optional[DetectedAlert]:
    status_date = record.get(Col.DATE_OF_CURRENT_STATUS)
    if not status_date:
        return DetectedAlert(
            category=AlertCategory.TRACKING_INACTIVITY,
            priority=Priority.MEDIUM,
            message="Date of Current Status is missing — cannot confirm the vehicle is being actively tracked.",
            rule_name="tracking_inactivity_missing_date",
        )
    inactive_days = (today - status_date).days
    if inactive_days >= thresholds.TRACKING_INACTIVITY_CRITICAL:
        priority = Priority.CRITICAL
    elif inactive_days >= thresholds.TRACKING_INACTIVITY_WARNING:
        priority = Priority.MEDIUM
    else:
        return None
    return DetectedAlert(
        category=AlertCategory.TRACKING_INACTIVITY,
        priority=priority,
        message=(
            f"No status update in {inactive_days} day(s) (last update: {status_date.isoformat()}). "
            f"[Prototype thresholds — warning={thresholds.TRACKING_INACTIVITY_WARNING}d, critical={thresholds.TRACKING_INACTIVITY_CRITICAL}d]"
        ),
        rule_name="tracking_inactivity",
    )


def detect_stationary_vehicle(record: dict, thresholds: AlertThresholds) -> Optional[DetectedAlert]:
    status = (record.get(Col.VEHICLE_STATUS) or "").strip().lower()
    days_at_location = record.get(Col.DAYS_AT_LOCATION)
    if status not in {"stationary", "idle"}:
        return None
    if days_at_location is None or days_at_location < thresholds.DAYS_AT_LOCATION_WARNING:
        return None
    return DetectedAlert(
        category=AlertCategory.STATIONARY_VEHICLE,
        priority=Priority.HIGH if days_at_location >= thresholds.DAYS_AT_LOCATION_HIGH else Priority.MEDIUM,
        message=f"Vehicle Status is '{record.get(Col.VEHICLE_STATUS)}' and has been at location for {days_at_location} day(s).",
        rule_name="stationary_vehicle",
    )


def detect_route_issue(record: dict) -> Optional[DetectedAlert]:
    missing = []
    if not record.get(Col.RUNNING_ROUTE):
        missing.append("Running Route")
    if not record.get(Col.FROM_CITY):
        missing.append("From City")
    if not record.get(Col.TO_CITY_1):
        missing.append("To City (First)")
    if not missing:
        return None
    return DetectedAlert(
        category=AlertCategory.ROUTE_ISSUE,
        priority=Priority.LOW,
        message=f"Route information incomplete: missing {', '.join(missing)}.",
        rule_name="route_info_incomplete",
    )


ALL_RULES = [
    "accident_keyword_match",
    "gps_not_working",
    "unloading_delay",
    "excessive_days_at_location",
    "transit_delay",
    "tracking_inactivity",
    "tracking_inactivity_missing_date",
    "stationary_vehicle",
    "route_info_incomplete",
]


def evaluate_record(record: dict, thresholds: AlertThresholds, today: Optional[dt.date] = None) -> list[DetectedAlert]:
    """Run every rule against one tracking record (as a plain dict of
    canonical-column -> typed value) and return all triggered alerts."""
    today = today or dt.date.today()
    detectors = [
        lambda r: detect_accident(r),
        lambda r: detect_gps_issue(r),
        lambda r: detect_unloading_delay(r, thresholds, today),
        lambda r: detect_excessive_days_at_location(r, thresholds),
        lambda r: detect_transit_delay(r, thresholds),
        lambda r: detect_tracking_inactivity(r, thresholds, today),
        lambda r: detect_stationary_vehicle(r, thresholds),
        lambda r: detect_route_issue(r),
    ]
    results = []
    for detector in detectors:
        alert = detector(record)
        if alert:
            results.append(alert)
    return results


def record_to_dict(tracking_record) -> dict:
    """Convert a SQLAlchemy TrackingRecord ORM object into the plain dict
    shape the rule functions expect."""
    return {
        Col.CARRIER_NUMBER: tracking_record.vehicle.carrier_number if tracking_record.vehicle else None,
        Col.VEHICLE_CATEGORY: tracking_record.vehicle.vehicle_category if tracking_record.vehicle else None,
        Col.RUNNING_ROUTE: tracking_record.running_route,
        Col.CONSIGNER: tracking_record.consigner,
        Col.LOAD_DATE: tracking_record.load_date,
        Col.DAYS_AT_LOCATION: tracking_record.days_at_location,
        Col.FROM_CITY: tracking_record.from_city,
        Col.TO_CITY_1: tracking_record.to_city_1,
        Col.EXPECTED_UNLOADING_DATE: tracking_record.expected_unloading_date,
        Col.ACTUAL_UNLOADING_DATE: tracking_record.actual_unloading_date,
        Col.DAYS_IN_TRANSIT: tracking_record.days_in_transit,
        Col.CURRENT_LOCATION: tracking_record.current_location,
        Col.STATE: tracking_record.state,
        Col.VEHICLE_STATUS: tracking_record.vehicle_status,
        Col.DATE_OF_CURRENT_STATUS: tracking_record.date_of_current_status,
        Col.GPS_WORKING: tracking_record.gps_working,
        Col.REMARKS: tracking_record.remarks,
    }
