"""SQLAlchemy ORM models. Tracking records are append-only: a new upload
never overwrites or deletes a previous tracking_records row, so historical
trend analysis stays possible."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Branch(Base):
    __tablename__ = "branches"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    code = Column(String(20), unique=True, nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    tracking_records = relationship("TrackingRecord", back_populates="branch")
    upload_batches = relationship("UploadBatch", back_populates="branch")


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True)
    carrier_number = Column(String(50), unique=True, nullable=False, index=True)
    vehicle_category = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    tracking_records = relationship("TrackingRecord", back_populates="vehicle")


class UploadBatch(Base):
    __tablename__ = "upload_batches"

    id = Column(Integer, primary_key=True)
    uploaded_at = Column(DateTime, default=dt.datetime.utcnow)
    source_filename = Column(String(255), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    status = Column(String(20), nullable=False, default="PENDING")  # SUCCESS/PARTIAL/FAILED
    row_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    is_synthetic = Column(Boolean, default=False)

    branch = relationship("Branch", back_populates="upload_batches")
    tracking_records = relationship("TrackingRecord", back_populates="upload_batch")


class TrackingRecord(Base):
    __tablename__ = "tracking_records"

    id = Column(Integer, primary_key=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    upload_batch_id = Column(Integer, ForeignKey("upload_batches.id"), nullable=False)

    running_route = Column(String(255))
    ytd_grade = Column(String(20))
    consigner = Column(String(255))

    load_date = Column(Date, nullable=True)
    exit_date = Column(Date, nullable=True)
    dispatch_date = Column(Date, nullable=True)
    days_at_location = Column(Integer, nullable=True)

    from_city = Column(String(100))
    to_city_1 = Column(String(100))
    to_city_2 = Column(String(100))
    to_city_3 = Column(String(100))

    expected_unloading_date = Column(Date, nullable=True)
    actual_unloading_date = Column(Date, nullable=True)
    next_loading_point_reach_date = Column(Date, nullable=True)
    days_in_transit = Column(Integer, nullable=True)

    current_location = Column(String(150))
    state = Column(String(100))
    next_loading_station = Column(String(150))

    vehicle_status = Column(String(50))
    date_of_current_status = Column(Date, nullable=True)
    gps_working = Column(String(10))
    entered_by_branch = Column(String(100))
    remarks = Column(Text)

    created_at = Column(DateTime, default=dt.datetime.utcnow)

    vehicle = relationship("Vehicle", back_populates="tracking_records")
    branch = relationship("Branch", back_populates="tracking_records")
    upload_batch = relationship("UploadBatch", back_populates="tracking_records")
    alerts = relationship("Alert", back_populates="tracking_record")


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    category = Column(String(50), nullable=False)
    priority = Column(String(20), nullable=False)
    condition_config = Column(Text)  # JSON-encoded config, e.g. thresholds used
    is_active = Column(Boolean, default=True)
    is_prototype = Column(Boolean, default=True)

    alerts = relationship("Alert", back_populates="rule")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)
    tracking_record_id = Column(Integer, ForeignKey("tracking_records.id"), nullable=False)
    rule_id = Column(Integer, ForeignKey("alert_rules.id"), nullable=True)

    category = Column(String(50), nullable=False)
    priority = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    detected_at = Column(DateTime, default=dt.datetime.utcnow)

    verified_by_human = Column(Boolean, nullable=True)  # None = not reviewed
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)

    tracking_record = relationship("TrackingRecord", back_populates="alerts")
    rule = relationship("AlertRule", back_populates="alerts")


class DailyReview(Base):
    __tablename__ = "daily_reviews"

    id = Column(Integer, primary_key=True)
    review_date = Column(Date, nullable=False, unique=True)
    generated_at = Column(DateTime, default=dt.datetime.utcnow)
    summary_json = Column(Text, nullable=False)
