"""
Generates the structured Daily Tracking Review.

Only Tracking data is real in Version 0.1. POD/Accounts/HR sections are
explicit "Coming Soon" placeholders — never fabricated statistics. Any
piece of information that cannot be determined from stored data is
labeled "Data not available." rather than guessed.
"""

from __future__ import annotations

import datetime as dt
import json

from sqlalchemy.orm import Session

from database.models import Alert, TrackingRecord, UploadBatch
from database.operations import save_daily_review
from utils.constants import Priority


def _batches_for_date(session: Session, review_date: dt.date) -> list[UploadBatch]:
    start = dt.datetime.combine(review_date, dt.time.min)
    end = dt.datetime.combine(review_date, dt.time.max)
    return (
        session.query(UploadBatch)
        .filter(UploadBatch.uploaded_at >= start, UploadBatch.uploaded_at <= end)
        .all()
    )


def _alerts_for_date(session: Session, review_date: dt.date) -> list[Alert]:
    start = dt.datetime.combine(review_date, dt.time.min)
    end = dt.datetime.combine(review_date, dt.time.max)
    return (
        session.query(Alert)
        .join(TrackingRecord, Alert.tracking_record_id == TrackingRecord.id)
        .filter(Alert.detected_at >= start, Alert.detected_at <= end)
        .all()
    )


def generate_daily_review(session: Session, review_date: dt.date | None = None) -> dict:
    review_date = review_date or dt.date.today()

    batches = _batches_for_date(session, review_date)
    alerts = _alerts_for_date(session, review_date)

    if not batches:
        report_status = {
            "branch_reports_received": "Data not available.",
            "processed_successfully": "Data not available.",
            "failed": "Data not available.",
            "vehicles_processed": "Data not available.",
        }
    else:
        report_status = {
            "branch_reports_received": len(batches),
            "processed_successfully": sum(1 for b in batches if b.status in {"SUCCESS", "PARTIAL"}),
            "failed": sum(1 for b in batches if b.status == "FAILED"),
            "vehicles_processed": sum(b.row_count or 0 for b in batches),
        }

    priority_counts = {p.value: 0 for p in Priority}
    for a in alerts:
        priority_counts[a.priority] = priority_counts.get(a.priority, 0) + 1

    total_vehicles = report_status.get("vehicles_processed")
    normal_vehicles = "Data not available."
    if isinstance(total_vehicles, int):
        flagged = len({a.tracking_record_id for a in alerts})
        normal_vehicles = max(total_vehicles - flagged, 0)

    operational_summary = {
        "total_vehicles": total_vehicles,
        "normal_vehicles": normal_vehicles,
        "critical_alerts": priority_counts.get("CRITICAL", 0),
        "high_alerts": priority_counts.get("HIGH", 0),
        "medium_alerts": priority_counts.get("MEDIUM", 0),
        "gps_issues": sum(1 for a in alerts if a.category == "GPS Issue"),
        "delayed_vehicles": sum(1 for a in alerts if a.category in {"Unloading Delay", "Transit Delay"}),
    }

    critical_issues = [
        f"[{a.category}] {a.tracking_record.vehicle.carrier_number if a.tracking_record and a.tracking_record.vehicle else 'Unknown vehicle'}: {a.message}"
        for a in alerts
        if a.priority == "CRITICAL"
    ]
    high_priority_issues = [
        f"[{a.category}] {a.tracking_record.vehicle.carrier_number if a.tracking_record and a.tracking_record.vehicle else 'Unknown vehicle'}: {a.message}"
        for a in alerts
        if a.priority == "HIGH"
    ]

    branch_summary = []
    branch_totals: dict[str, dict] = {}
    for b in batches:
        name = b.branch.name if b.branch else "Unknown"
        entry = branch_totals.setdefault(name, {"branch": name, "vehicles": 0, "status": "SUCCESS"})
        entry["vehicles"] += b.row_count or 0
        if b.status == "FAILED":
            entry["status"] = "FAILED"
        elif b.status == "PARTIAL" and entry["status"] != "FAILED":
            entry["status"] = "PARTIAL"
    branch_summary = list(branch_totals.values())

    recommended_follow_up = []
    if operational_summary["critical_alerts"]:
        recommended_follow_up.append(
            f"Immediately verify {operational_summary['critical_alerts']} CRITICAL alert(s) — accidents and severe conditions need human confirmation first."
        )
    if operational_summary["gps_issues"]:
        recommended_follow_up.append(f"Investigate {operational_summary['gps_issues']} vehicle(s) with GPS not working.")
    if operational_summary["delayed_vehicles"]:
        recommended_follow_up.append(f"Follow up with branches on {operational_summary['delayed_vehicles']} delayed vehicle(s).")
    if not batches:
        recommended_follow_up.append("No branch reports were uploaded for this date — confirm all branches have submitted their Tracking report.")
    if not recommended_follow_up:
        recommended_follow_up.append("No action items identified from today's data.")

    review = {
        "review_date": review_date.isoformat(),
        "report_status": report_status,
        "operational_summary": operational_summary,
        "critical_issues": critical_issues,
        "high_priority_issues": high_priority_issues,
        "branch_summary": branch_summary,
        "recommended_follow_up": recommended_follow_up,
        "pod_status": "Coming Soon — Module not yet implemented.",
        "accounts_status": "Coming Soon — Module not yet implemented.",
        "hr_status": "Coming Soon — Module not yet implemented.",
    }

    save_daily_review(session, review_date, json.dumps(review))
    return review
