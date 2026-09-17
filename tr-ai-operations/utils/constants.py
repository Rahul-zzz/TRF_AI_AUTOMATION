"""
Central definitions for canonical field names, enums and accepted-value lists.

Keeping these in one place means the column mapper, validator, alert engine
and UI all agree on spelling/casing, and new accepted spreadsheet variants
only need to be added here.
"""

from enum import Enum


# ---------------------------------------------------------------------------
# Canonical internal column names (used everywhere after normalization)
# ---------------------------------------------------------------------------
class Col:
    SL_NO = "sl_no"
    CARRIER_NUMBER = "carrier_number"
    VEHICLE_CATEGORY = "vehicle_category"
    RUNNING_ROUTE = "running_route"
    YTD_GRADE = "ytd_grade"
    CONSIGNER = "consigner"
    LOAD_DATE = "load_date"
    EXIT_DATE = "exit_date"
    DISPATCH_DATE = "dispatch_date"
    DAYS_AT_LOCATION = "days_at_location"
    FROM_CITY = "from_city"
    TO_CITY_1 = "to_city_1"
    TO_CITY_2 = "to_city_2"
    TO_CITY_3 = "to_city_3"
    EXPECTED_UNLOADING_DATE = "expected_unloading_date"
    ACTUAL_UNLOADING_DATE = "actual_unloading_date"
    NEXT_LOADING_POINT_REACH_DATE = "next_loading_point_reach_date"
    DAYS_IN_TRANSIT = "days_in_transit"
    CURRENT_LOCATION = "current_location"
    STATE = "state"
    NEXT_LOADING_STATION = "next_loading_station"
    VEHICLE_STATUS = "vehicle_status"
    DATE_OF_CURRENT_STATUS = "date_of_current_status"
    GPS_WORKING = "gps_working"
    ENTERED_BY_BRANCH = "entered_by_branch"
    REMARKS = "remarks"


# Columns that MUST be present (after normalization) for a row to be usable.
REQUIRED_COLUMNS = [
    Col.CARRIER_NUMBER,
    Col.VEHICLE_CATEGORY,
    Col.VEHICLE_STATUS,
]

# All 26 columns from the spec, in original order — used to build the
# synthetic generator and to report "expected but entirely missing" columns.
ALL_EXPECTED_COLUMNS = [
    Col.SL_NO,
    Col.CARRIER_NUMBER,
    Col.VEHICLE_CATEGORY,
    Col.RUNNING_ROUTE,
    Col.YTD_GRADE,
    Col.CONSIGNER,
    Col.LOAD_DATE,
    Col.EXIT_DATE,
    Col.DISPATCH_DATE,
    Col.DAYS_AT_LOCATION,
    Col.FROM_CITY,
    Col.TO_CITY_1,
    Col.TO_CITY_2,
    Col.TO_CITY_3,
    Col.EXPECTED_UNLOADING_DATE,
    Col.ACTUAL_UNLOADING_DATE,
    Col.NEXT_LOADING_POINT_REACH_DATE,
    Col.DAYS_IN_TRANSIT,
    Col.CURRENT_LOCATION,
    Col.STATE,
    Col.NEXT_LOADING_STATION,
    Col.VEHICLE_STATUS,
    Col.DATE_OF_CURRENT_STATUS,
    Col.GPS_WORKING,
    Col.ENTERED_BY_BRANCH,
    Col.REMARKS,
]

DATE_COLUMNS = [
    Col.LOAD_DATE,
    Col.EXIT_DATE,
    Col.DISPATCH_DATE,
    Col.EXPECTED_UNLOADING_DATE,
    Col.ACTUAL_UNLOADING_DATE,
    Col.NEXT_LOADING_POINT_REACH_DATE,
    Col.DATE_OF_CURRENT_STATUS,
]

NUMERIC_COLUMNS = [
    Col.DAYS_AT_LOCATION,
    Col.DAYS_IN_TRANSIT,
]

# Human-friendly display names for the canonical columns.
DISPLAY_NAMES = {
    Col.SL_NO: "Sl. No",
    Col.CARRIER_NUMBER: "Carrier Number",
    Col.VEHICLE_CATEGORY: "Vehicle Category",
    Col.RUNNING_ROUTE: "Running Route",
    Col.YTD_GRADE: "YTD Grade",
    Col.CONSIGNER: "Consigner",
    Col.LOAD_DATE: "Load Date",
    Col.EXIT_DATE: "Exit Date",
    Col.DISPATCH_DATE: "Dispatch Date",
    Col.DAYS_AT_LOCATION: "# Days at Location",
    Col.FROM_CITY: "From City",
    Col.TO_CITY_1: "To City (FIRST)",
    Col.TO_CITY_2: "To City (SECOND)",
    Col.TO_CITY_3: "To City (THIRD)",
    Col.EXPECTED_UNLOADING_DATE: "Expected Unloading Date",
    Col.ACTUAL_UNLOADING_DATE: "Actual Unloading Date",
    Col.NEXT_LOADING_POINT_REACH_DATE: "Next Loading Point Reach Date",
    Col.DAYS_IN_TRANSIT: "# Days in Transit",
    Col.CURRENT_LOCATION: "Current Location",
    Col.STATE: "State",
    Col.NEXT_LOADING_STATION: "Next Loading Station",
    Col.VEHICLE_STATUS: "Vehicle Status",
    Col.DATE_OF_CURRENT_STATUS: "Date of Current Status",
    Col.GPS_WORKING: "GPS Working",
    Col.ENTERED_BY_BRANCH: "Entered By Branch",
    Col.REMARKS: "Remarks",
}


# ---------------------------------------------------------------------------
# Accepted value sets (used for validation warnings, not hard rejection)
# ---------------------------------------------------------------------------
KNOWN_VEHICLE_STATUSES = [
    "In Transit",
    "Loading",
    "Unloading",
    "At Branch",
    "Stationary",
    "Delivered",
    "Breakdown",
    "Accident",
    "Under Repair",
    "Idle",
]

KNOWN_GPS_VALUES = ["Yes", "No"]

KNOWN_BRANCHES = [
    "Chennai",
    "Delhi",
    "Mumbai",
    "Pune",
    "Bangalore",
    "Hyderabad",
    "Ahmedabad",
    "Kolkata",
]

VEHICLE_CATEGORIES = [
    "Multi-Axle Trailer",
    "Car Carrier",
    "Rigid Truck",
    "Container Trailer",
    "Open Body Trailer",
]


# ---------------------------------------------------------------------------
# Validation severities
# ---------------------------------------------------------------------------
class Severity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


# ---------------------------------------------------------------------------
# Alert categories & priorities
# ---------------------------------------------------------------------------
class AlertCategory(str, Enum):
    ACCIDENT = "Accident"
    SEVERE_DELAY = "Severe Delay"
    TRACKING_INACTIVITY = "Tracking Inactivity"
    GPS_ISSUE = "GPS Issue"
    EXCESSIVE_DAYS_AT_LOCATION = "Excessive Days at Location"
    TRANSIT_DELAY = "Transit Delay"
    UNLOADING_DELAY = "Unloading Delay"
    STATIONARY_VEHICLE = "Stationary Vehicle"
    ROUTE_ISSUE = "Route Issue"
    FUEL_INEFFICIENCY = "Fuel Inefficiency"  # future, not calculated yet
    DATA_QUALITY = "Data Quality"


class Priority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


PRIORITY_ICON = {
    Priority.CRITICAL: "\U0001F534",  # red circle
    Priority.HIGH: "\U0001F7E0",      # orange circle
    Priority.MEDIUM: "\U0001F7E1",    # yellow circle
    Priority.LOW: "\U0001F535",       # blue circle
}

PRIORITY_ORDER = [Priority.CRITICAL, Priority.HIGH, Priority.MEDIUM, Priority.LOW]

ACCIDENT_KEYWORDS = [
    "accident",
    "collision",
    "crash",
    "damaged",
    "damage",
    "breakdown",
    "stranded",
]

SYNTHETIC_DATA_LABEL = "SYNTHETIC DEMO DATA \u2014 NOT REAL COMPANY DATA"
