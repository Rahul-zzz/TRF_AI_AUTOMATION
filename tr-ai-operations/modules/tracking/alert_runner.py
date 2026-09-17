"""Bridges the pure alert-detection rules (alerts.py) to the database:
runs the engine over TrackingRecord rows and persists Alert rows,
creating/reusing AlertRule entries so every alert traces back to an
explicit, named rule."""

from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from config.settings import SETTINGS
from database.models import TrackingRecord
from database.operations import get_or_create_alert_rule, save_alert
from modules.tracking.alerts import evaluate_record, record_to_dict

RULE_NAME_TO_META = {
    "accident_keyword_match": ("Accident", "CRITICAL"),
    "gps_not_working": ("GPS Issue", "HIGH"),
    "unloading_delay": ("Unloading Delay", "HIGH"),  # priority is per-alert, this is just the default label
    "excessive_days_at_location": ("Excessive Days at Location", "MEDIUM"),
    "transit_delay": ("Transit Delay", "MEDIUM"),
    "tracking_inactivity": ("Tracking Inactivity", "MEDIUM"),
    "tracking_inactivity_missing_date": ("Tracking Inactivity", "MEDIUM"),
    "stationary_vehicle": ("Stationary Vehicle", "MEDIUM"),
    "route_info_incomplete": ("Route Issue", "LOW"),
}


def run_alert_engine_for_records(session: Session, tracking_records: list[TrackingRecord], today: dt.date | None = None) -> int:
    """Evaluate every rule against each record and persist triggered alerts.
    Returns the number of alerts created."""
    thresholds = SETTINGS.thresholds
    today = today or dt.date.today()
    created = 0

    for tr in tracking_records:
        record_dict = record_to_dict(tr)
        detected = evaluate_record(record_dict, thresholds, today)
        for alert in detected:
            category, default_priority = RULE_NAME_TO_META.get(alert.rule_name, (alert.category.value, alert.priority.value))
            rule = get_or_create_alert_rule(
                session,
                name=alert.rule_name,
                category=category,
                priority=default_priority,
                condition_config="see config/settings.py:AlertThresholds",
                is_prototype=True,
            )
            save_alert(
                session,
                tracking_record=tr,
                rule=rule,
                category=alert.category.value,
                priority=alert.priority.value,
                message=alert.message,
            )
            created += 1

    return created
