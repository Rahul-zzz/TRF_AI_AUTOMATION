"""
Generates realistic, clearly-labeled SYNTHETIC demo data matching the
26-column Tracking Excel structure, deliberately including edge cases
(accidents, GPS failures, excessive location time, transit delays,
unloading delays, missing values, data-quality issues) so every alert
rule and dashboard element has something to react to.

This data is NEVER a stand-in for real company data and must not be
mixed with it — each synthetic upload batch is flagged is_synthetic=True
in the database.
"""

from __future__ import annotations

import datetime as dt
import random

import pandas as pd

from utils.constants import (
    ALL_EXPECTED_COLUMNS,
    DISPLAY_NAMES,
    KNOWN_BRANCHES,
    VEHICLE_CATEGORIES,
    Col,
)

ROUTES = [
    "Chennai-Delhi", "Mumbai-Pune", "Bangalore-Hyderabad", "Ahmedabad-Kolkata",
    "Delhi-Mumbai", "Pune-Bangalore", "Hyderabad-Chennai", "Kolkata-Ahmedabad",
]
CITIES = ["Chennai", "Delhi", "Mumbai", "Pune", "Bangalore", "Hyderabad", "Ahmedabad", "Kolkata", "Nagpur", "Indore"]
STATES = ["Tamil Nadu", "Delhi", "Maharashtra", "Karnataka", "Telangana", "Gujarat", "West Bengal", "Madhya Pradesh"]
CONSIGNERS = ["Maruti Suzuki", "Tata Motors", "Hyundai Motors", "Mahindra", "Kia India", "Toyota Kirloskar"]
STATUSES = [
    "In Transit", "Loading", "Unloading", "At Branch", "Stationary",
    "Delivered", "Breakdown", "Accident", "Under Repair", "Idle",
]
NORMAL_REMARKS = ["", "On schedule", "No issues reported", "Routine stop", "Awaiting documentation"]
ACCIDENT_REMARKS = [
    "Minor accident reported near toll plaza, driver safe",
    "Collision with another vehicle, assessing damage",
    "Vehicle damaged during loading, under inspection",
]


def _random_date(start_days_ago: int, end_days_ago: int) -> dt.date:
    today = dt.date.today()
    delta = random.randint(end_days_ago, start_days_ago)
    return today - dt.timedelta(days=delta)


def _carrier_number(i: int) -> str:
    return f"TN{random.randint(10,99)}AB{1000+i}"


def generate_synthetic_tracking_dataframe(num_vehicles: int = 220, seed: int | None = None, branch: str | None = None) -> pd.DataFrame:
    """Generate one dataframe. If `branch` is given, every row uses that
    branch (matching how a real single-branch export looks); otherwise
    branch is randomized per row, which is only useful for quick single-file
    smoke testing, not for realistic multi-branch consolidation testing —
    use generate_synthetic_multi_branch_files() for that."""
    if seed is not None:
        random.seed(seed)

    rows = []
    for i in range(num_vehicles):
        row_branch = branch or random.choice(KNOWN_BRANCHES)
        category = random.choice(VEHICLE_CATEGORIES)
        route = random.choice(ROUTES)
        from_city, to_city_1 = route.split("-")
        status = random.choices(STATUSES, weights=[30, 10, 10, 10, 10, 8, 3, 2, 4, 5])[0]

        load_date = _random_date(20, 3)
        dispatch_date = load_date + dt.timedelta(days=random.randint(0, 1))
        exit_date = dispatch_date + dt.timedelta(days=random.randint(0, 1))
        expected_unloading_date = dispatch_date + dt.timedelta(days=random.randint(2, 6))

        # Edge-case distribution
        roll = random.random()
        days_at_location = random.randint(0, 2)
        days_in_transit = random.randint(0, 3)
        gps_working = "Yes"
        actual_unloading_date = None
        remarks = random.choice(NORMAL_REMARKS)
        date_of_current_status = _random_date(2, 0)

        if roll < 0.05:
            # Accident case
            status = "Accident"
            remarks = random.choice(ACCIDENT_REMARKS)
        elif roll < 0.15:
            # GPS failure
            gps_working = "No"
        elif roll < 0.25:
            # Excessive days at location
            days_at_location = random.randint(4, 12)
            status = "Stationary"
        elif roll < 0.33:
            # Transit delay
            days_in_transit = random.randint(6, 14)
            status = "In Transit"
        elif roll < 0.42:
            # Unloading delay: expected date already passed, no actual date
            expected_unloading_date = _random_date(7, 1)
            actual_unloading_date = None
        elif roll < 0.47:
            # Tracking inactivity: stale status date
            date_of_current_status = _random_date(10, 4)
        elif roll < 0.52:
            # Data quality issue: missing branch (only when branch isn't pinned)
            if branch is None and random.random() < 0.5:
                row_branch = ""
        else:
            # Normal / delivered
            if status == "Delivered":
                actual_unloading_date = expected_unloading_date + dt.timedelta(days=random.randint(-1, 1))

        row = {
            Col.SL_NO: i + 1,
            Col.CARRIER_NUMBER: _carrier_number(i),
            Col.VEHICLE_CATEGORY: category,
            Col.RUNNING_ROUTE: route,
            Col.YTD_GRADE: random.choice(["A", "B", "C"]),
            Col.CONSIGNER: random.choice(CONSIGNERS),
            Col.LOAD_DATE: load_date,
            Col.EXIT_DATE: exit_date,
            Col.DISPATCH_DATE: dispatch_date,
            Col.DAYS_AT_LOCATION: days_at_location,
            Col.FROM_CITY: from_city,
            Col.TO_CITY_1: to_city_1,
            Col.TO_CITY_2: random.choice(CITIES) if random.random() < 0.3 else "",
            Col.TO_CITY_3: "",
            Col.EXPECTED_UNLOADING_DATE: expected_unloading_date,
            Col.ACTUAL_UNLOADING_DATE: actual_unloading_date,
            Col.NEXT_LOADING_POINT_REACH_DATE: expected_unloading_date + dt.timedelta(days=random.randint(1, 3)),
            Col.DAYS_IN_TRANSIT: days_in_transit,
            Col.CURRENT_LOCATION: random.choice(CITIES),
            Col.STATE: random.choice(STATES),
            Col.NEXT_LOADING_STATION: random.choice(CITIES),
            Col.VEHICLE_STATUS: status,
            Col.DATE_OF_CURRENT_STATUS: date_of_current_status,
            Col.GPS_WORKING: gps_working,
            Col.ENTERED_BY_BRANCH: row_branch,
            Col.REMARKS: remarks,
        }
        rows.append(row)

    df = pd.DataFrame(rows, columns=ALL_EXPECTED_COLUMNS)
    return df


def generate_synthetic_multi_branch_files(
    branches: list[str] | None = None, vehicles_per_branch: int = 25, seed: int | None = None
) -> dict[str, pd.DataFrame]:
    """Generate one realistic per-branch dataframe for each branch, so the
    multi-branch upload/consolidation flow can be tested the way it will
    actually be used: one file per branch, each internally consistent."""
    branches = branches or KNOWN_BRANCHES
    if seed is not None:
        random.seed(seed)
    files = {}
    start_index = 0
    for branch in branches:
        df = generate_synthetic_tracking_dataframe(num_vehicles=vehicles_per_branch, branch=branch)
        # Re-number Sl. No and carrier numbers so they don't collide across branches
        df[Col.SL_NO] = range(start_index + 1, start_index + 1 + len(df))
        df[Col.CARRIER_NUMBER] = [f"{branch[:2].upper()}{random.randint(10,99)}AB{2000 + start_index + i}" for i in range(len(df))]
        files[branch] = df
        start_index += vehicles_per_branch
    return files


def to_display_excel_bytes(df: pd.DataFrame) -> bytes:
    """Rename canonical columns back to their original display names
    (as they'd appear in a real branch export) before writing to Excel,
    so the demo file looks like a genuine Tracking report."""
    import io

    display_df = df.rename(columns=DISPLAY_NAMES)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        display_df.to_excel(writer, index=False, sheet_name="Tracking")
    return buffer.getvalue()
