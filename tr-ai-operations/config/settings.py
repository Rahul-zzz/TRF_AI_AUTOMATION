"""
Application configuration.

IMPORTANT: The numeric thresholds below are PROTOTYPE ASSUMPTIONS only.
They are not official TR Finished Vehicles Logistics business rules.
They exist so the alert engine has *something* explainable and testable
to run against, and so they can be tuned from one place (or the Settings
page) once operations staff validate real-world numbers.

Every threshold can be overridden with an environment variable of the
same name (see .env.example) without touching code.
"""

import os
from dataclasses import dataclass, field

try:
    from dotenv import load_dotenv

    load_dotenv()  # loads .env if present; silently does nothing otherwise
except ImportError:  # pragma: no cover - optional dependency
    pass


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


@dataclass
class AlertThresholds:
    """All values are PROTOTYPE thresholds pending validation by TR staff."""

    is_prototype: bool = True

    # Days at Location
    DAYS_AT_LOCATION_WARNING: int = field(default_factory=lambda: _env_int("DAYS_AT_LOCATION_WARNING", 3))
    DAYS_AT_LOCATION_HIGH: int = field(default_factory=lambda: _env_int("DAYS_AT_LOCATION_HIGH", 5))
    DAYS_AT_LOCATION_CRITICAL: int = field(default_factory=lambda: _env_int("DAYS_AT_LOCATION_CRITICAL", 8))

    # Days in Transit
    DAYS_IN_TRANSIT_WARNING: int = field(default_factory=lambda: _env_int("DAYS_IN_TRANSIT_WARNING", 5))
    DAYS_IN_TRANSIT_HIGH: int = field(default_factory=lambda: _env_int("DAYS_IN_TRANSIT_HIGH", 8))

    # Unloading delay (days past Expected Unloading Date with no Actual date)
    UNLOADING_DELAY_HIGH: int = field(default_factory=lambda: _env_int("UNLOADING_DELAY_HIGH", 1))
    UNLOADING_DELAY_CRITICAL: int = field(default_factory=lambda: _env_int("UNLOADING_DELAY_CRITICAL", 4))

    # Tracking inactivity (days since Date of Current Status)
    TRACKING_INACTIVITY_WARNING: int = field(default_factory=lambda: _env_int("TRACKING_INACTIVITY_WARNING", 2))
    TRACKING_INACTIVITY_CRITICAL: int = field(default_factory=lambda: _env_int("TRACKING_INACTIVITY_CRITICAL", 5))

    # Duplicate-upload detection window (days)
    DUPLICATE_WINDOW_DAYS: int = field(default_factory=lambda: _env_int("DUPLICATE_WINDOW_DAYS", 1))


@dataclass
class AppSettings:
    app_name: str = "TR AI Operations Platform"
    app_subtitle: str = "Intelligent Logistics Operations & Daily Review System"
    company_name: str = "TR Finished Vehicles Logistics Solutions Limited"
    database_path: str = os.environ.get("DATABASE_PATH", "data/tr_operations.db")
    uploads_dir: str = "data/uploads"
    processed_dir: str = "data/processed"
    exports_dir: str = "data/exports"
    demo_dir: str = "data/demo"
    thresholds: AlertThresholds = field(default_factory=AlertThresholds)


SETTINGS = AppSettings()
