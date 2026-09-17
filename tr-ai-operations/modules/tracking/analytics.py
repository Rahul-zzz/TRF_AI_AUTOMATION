"""
Computes dashboard KPIs and branch-level analytics directly from the
database. Every number here is derived from stored tracking_records /
alerts — nothing is invented or hardcoded.
"""

from __future__ import annotations

from collections import Counter, defaultdict

import pandas as pd
from sqlalchemy.orm import Session

from database.operations import alerts_for_records, latest_tracking_records
from utils.constants import Priority


def _latest_state(session: Session):
    """Returns (list_of_TrackingRecord, dict[record_id -> list[Alert]])."""
    records = latest_tracking_records(session)
    record_ids = [r.id for r in records]
    alerts = alerts_for_records(session, record_ids)
    alerts_by_record = defaultdict(list)
    for a in alerts:
        alerts_by_record[a.tracking_record_id].append(a)
    return records, alerts_by_record


def compute_kpis(session: Session) -> dict:
    records, alerts_by_record = _latest_state(session)

    if not records:
        return {"has_data": False}

    priority_counts = Counter()
    gps_issues = 0
    delayed = 0
    for r in records:
        for a in alerts_by_record.get(r.id, []):
            priority_counts[a.priority] += 1
            if a.category == "GPS Issue":
                gps_issues += 1
            if a.category in {"Unloading Delay", "Transit Delay", "Severe Delay"}:
                delayed += 1

    in_transit = sum(1 for r in records if (r.vehicle_status or "").strip().lower() == "in transit")
    normal_vehicles = sum(1 for r in records if not alerts_by_record.get(r.id))
    branches = {r.branch.name for r in records if r.branch}

    return {
        "has_data": True,
        "total_vehicles": len(records),
        "normal_vehicles": normal_vehicles,
        "critical_alerts": priority_counts.get(Priority.CRITICAL.value, 0),
        "high_alerts": priority_counts.get(Priority.HIGH.value, 0),
        "medium_alerts": priority_counts.get(Priority.MEDIUM.value, 0),
        "low_alerts": priority_counts.get(Priority.LOW.value, 0),
        "gps_issues": gps_issues,
        "delayed_vehicles": delayed,
        "in_transit": in_transit,
        "branches_processed": len(branches),
    }


def vehicle_status_distribution(session: Session) -> pd.DataFrame:
    records, _ = _latest_state(session)
    counts = Counter((r.vehicle_status or "Unknown") for r in records)
    return pd.DataFrame({"status": list(counts.keys()), "count": list(counts.values())})


def alerts_by_priority(session: Session) -> pd.DataFrame:
    _, alerts_by_record = _latest_state(session)
    counts = Counter()
    for alerts in alerts_by_record.values():
        for a in alerts:
            counts[a.priority] += 1
    order = [p.value for p in Priority]
    return pd.DataFrame({"priority": order, "count": [counts.get(p, 0) for p in order]})


def alerts_by_category(session: Session) -> pd.DataFrame:
    _, alerts_by_record = _latest_state(session)
    counts = Counter()
    for alerts in alerts_by_record.values():
        for a in alerts:
            counts[a.category] += 1
    return pd.DataFrame({"category": list(counts.keys()), "count": list(counts.values())})


def alerts_by_branch(session: Session) -> pd.DataFrame:
    records, alerts_by_record = _latest_state(session)
    counts = Counter()
    for r in records:
        branch_name = r.branch.name if r.branch else "Unknown"
        counts[branch_name] += len(alerts_by_record.get(r.id, []))
    return pd.DataFrame({"branch": list(counts.keys()), "count": list(counts.values())})


def vehicles_by_branch(session: Session) -> pd.DataFrame:
    records, _ = _latest_state(session)
    counts = Counter((r.branch.name if r.branch else "Unknown") for r in records)
    return pd.DataFrame({"branch": list(counts.keys()), "count": list(counts.values())})


def gps_status_distribution(session: Session) -> pd.DataFrame:
    records, _ = _latest_state(session)
    counts = Counter((r.gps_working or "Unknown") for r in records)
    return pd.DataFrame({"gps_working": list(counts.keys()), "count": list(counts.values())})


def days_at_location_distribution(session: Session) -> pd.DataFrame:
    records, _ = _latest_state(session)
    values = [r.days_at_location for r in records if r.days_at_location is not None]
    return pd.DataFrame({"days_at_location": values})


def days_in_transit_distribution(session: Session) -> pd.DataFrame:
    records, _ = _latest_state(session)
    values = [r.days_in_transit for r in records if r.days_in_transit is not None]
    return pd.DataFrame({"days_in_transit": values})


def branch_summary(session: Session) -> pd.DataFrame:
    records, alerts_by_record = _latest_state(session)
    rows = []
    by_branch = defaultdict(list)
    for r in records:
        branch_name = r.branch.name if r.branch else "Unknown"
        by_branch[branch_name].append(r)

    for branch_name, branch_records in sorted(by_branch.items()):
        critical = high = gps_issues = delayed = 0
        for r in branch_records:
            for a in alerts_by_record.get(r.id, []):
                if a.priority == Priority.CRITICAL.value:
                    critical += 1
                if a.priority == Priority.HIGH.value:
                    high += 1
                if a.category == "GPS Issue":
                    gps_issues += 1
                if a.category in {"Unloading Delay", "Transit Delay"}:
                    delayed += 1
        active = sum(1 for r in branch_records if (r.vehicle_status or "").strip().lower() not in {"delivered", ""})
        rows.append(
            {
                "branch": branch_name,
                "total_vehicles": len(branch_records),
                "active_vehicles": active,
                "critical_alerts": critical,
                "high_alerts": high,
                "gps_issues": gps_issues,
                "delayed_vehicles": delayed,
            }
        )
    return pd.DataFrame(rows)


def search_vehicles(
    session: Session,
    carrier_number: str = "",
    branch: str = "",
    current_location: str = "",
    vehicle_status: str = "",
    consigner: str = "",
    state: str = "",
) -> list:
    records, _ = _latest_state(session)

    def match(text, needle):
        if not needle:
            return True
        return needle.strip().lower() in (text or "").strip().lower()

    results = []
    for r in records:
        if not match(r.vehicle.carrier_number if r.vehicle else "", carrier_number):
            continue
        if not match(r.branch.name if r.branch else "", branch):
            continue
        if not match(r.current_location, current_location):
            continue
        if not match(r.vehicle_status, vehicle_status):
            continue
        if not match(r.consigner, consigner):
            continue
        if not match(r.state, state):
            continue
        results.append(r)
    return results
