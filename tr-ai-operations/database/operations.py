"""Database read/write helpers. No business logic beyond simple lookups —
alert rules and analytics live in modules/tracking/."""

from __future__ import annotations

import datetime as dt
from typing import Iterable, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from database.models import (
    Alert,
    AlertRule,
    Branch,
    DailyReview,
    TrackingRecord,
    UploadBatch,
    Vehicle,
)
from utils.constants import Col


def get_or_create_branch(session: Session, name: str, code: Optional[str] = None) -> Branch:
    name = (name or "Unknown").strip()
    branch = session.query(Branch).filter(func.lower(Branch.name) == name.lower()).first()
    if branch:
        return branch
    branch = Branch(name=name, code=code)
    session.add(branch)
    session.flush()
    return branch


def get_or_create_vehicle(session: Session, carrier_number: str, vehicle_category: Optional[str] = None) -> Vehicle:
    carrier_number = carrier_number.strip()
    vehicle = session.query(Vehicle).filter(Vehicle.carrier_number == carrier_number).first()
    if vehicle:
        if vehicle_category and not vehicle.vehicle_category:
            vehicle.vehicle_category = vehicle_category
        return vehicle
    vehicle = Vehicle(carrier_number=carrier_number, vehicle_category=vehicle_category)
    session.add(vehicle)
    session.flush()
    return vehicle


def create_upload_batch(
    session: Session,
    source_filename: str,
    branch: Optional[Branch] = None,
    is_synthetic: bool = False,
) -> UploadBatch:
    batch = UploadBatch(
        source_filename=source_filename,
        branch_id=branch.id if branch else None,
        status="PENDING",
        is_synthetic=is_synthetic,
    )
    session.add(batch)
    session.flush()
    return batch


def find_possible_duplicate(
    session: Session, carrier_number: str, load_date, branch_id: Optional[int], window_days: int
) -> Optional[TrackingRecord]:
    """A likely duplicate = same carrier number + same load date (+/- window)
    + same branch, already stored. This is a heuristic, not a guarantee."""
    if not load_date:
        return None
    vehicle = session.query(Vehicle).filter(Vehicle.carrier_number == carrier_number).first()
    if not vehicle:
        return None
    window = dt.timedelta(days=window_days)
    query = (
        session.query(TrackingRecord)
        .filter(TrackingRecord.vehicle_id == vehicle.id)
        .filter(TrackingRecord.load_date.isnot(None))
        .filter(TrackingRecord.load_date >= load_date - window)
        .filter(TrackingRecord.load_date <= load_date + window)
    )
    if branch_id is not None:
        query = query.filter(TrackingRecord.branch_id == branch_id)
    return query.first()


def insert_tracking_record(session: Session, batch: UploadBatch, branch: Branch, row: dict) -> TrackingRecord:
    vehicle = get_or_create_vehicle(session, row[Col.CARRIER_NUMBER], row.get(Col.VEHICLE_CATEGORY))
    record = TrackingRecord(
        vehicle_id=vehicle.id,
        branch_id=branch.id if branch else None,
        upload_batch_id=batch.id,
        running_route=row.get(Col.RUNNING_ROUTE),
        ytd_grade=row.get(Col.YTD_GRADE),
        consigner=row.get(Col.CONSIGNER),
        load_date=row.get(Col.LOAD_DATE),
        exit_date=row.get(Col.EXIT_DATE),
        dispatch_date=row.get(Col.DISPATCH_DATE),
        days_at_location=row.get(Col.DAYS_AT_LOCATION),
        from_city=row.get(Col.FROM_CITY),
        to_city_1=row.get(Col.TO_CITY_1),
        to_city_2=row.get(Col.TO_CITY_2),
        to_city_3=row.get(Col.TO_CITY_3),
        expected_unloading_date=row.get(Col.EXPECTED_UNLOADING_DATE),
        actual_unloading_date=row.get(Col.ACTUAL_UNLOADING_DATE),
        next_loading_point_reach_date=row.get(Col.NEXT_LOADING_POINT_REACH_DATE),
        days_in_transit=row.get(Col.DAYS_IN_TRANSIT),
        current_location=row.get(Col.CURRENT_LOCATION),
        state=row.get(Col.STATE),
        next_loading_station=row.get(Col.NEXT_LOADING_STATION),
        vehicle_status=row.get(Col.VEHICLE_STATUS),
        date_of_current_status=row.get(Col.DATE_OF_CURRENT_STATUS),
        gps_working=row.get(Col.GPS_WORKING),
        entered_by_branch=row.get(Col.ENTERED_BY_BRANCH),
        remarks=row.get(Col.REMARKS),
    )
    session.add(record)
    session.flush()
    return record


def get_or_create_alert_rule(
    session: Session, name: str, category: str, priority: str, condition_config: str = "", is_prototype: bool = True
) -> AlertRule:
    rule = session.query(AlertRule).filter(AlertRule.name == name).first()
    if rule:
        return rule
    rule = AlertRule(
        name=name,
        category=category,
        priority=priority,
        condition_config=condition_config,
        is_active=True,
        is_prototype=is_prototype,
    )
    session.add(rule)
    session.flush()
    return rule


def save_alert(session: Session, tracking_record: TrackingRecord, rule: AlertRule, category: str, priority: str, message: str) -> Alert:
    alert = Alert(
        tracking_record_id=tracking_record.id,
        rule_id=rule.id if rule else None,
        category=category,
        priority=priority,
        message=message,
        verified_by_human=None,
        resolved=False,
    )
    session.add(alert)
    session.flush()
    return alert


def latest_tracking_records(session: Session) -> list[TrackingRecord]:
    """One row per vehicle: the most recent tracking_records entry
    (by date_of_current_status, falling back to created_at)."""
    all_records = session.query(TrackingRecord).all()
    latest_by_vehicle: dict[int, TrackingRecord] = {}
    for rec in all_records:
        current = latest_by_vehicle.get(rec.vehicle_id)
        if current is None:
            latest_by_vehicle[rec.vehicle_id] = rec
            continue
        rec_key = (rec.date_of_current_status or dt.date.min, rec.created_at or dt.datetime.min)
        cur_key = (current.date_of_current_status or dt.date.min, current.created_at or dt.datetime.min)
        if rec_key > cur_key:
            latest_by_vehicle[rec.vehicle_id] = rec
    return list(latest_by_vehicle.values())


def alerts_for_records(session: Session, record_ids: Iterable[int]) -> list[Alert]:
    record_ids = list(record_ids)
    if not record_ids:
        return []
    return session.query(Alert).filter(Alert.tracking_record_id.in_(record_ids)).all()


def all_branches(session: Session) -> list[Branch]:
    return session.query(Branch).order_by(Branch.name).all()


def save_daily_review(session: Session, review_date: dt.date, summary_json: str) -> DailyReview:
    existing = session.query(DailyReview).filter(DailyReview.review_date == review_date).first()
    if existing:
        existing.summary_json = summary_json
        existing.generated_at = dt.datetime.utcnow()
        session.flush()
        return existing
    review = DailyReview(review_date=review_date, summary_json=summary_json)
    session.add(review)
    session.flush()
    return review
