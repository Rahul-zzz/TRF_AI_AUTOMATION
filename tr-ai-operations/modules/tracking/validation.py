"""
Validates a normalized tracking dataframe row by row.

Never silently repairs data. Every questionable value is surfaced as an
issue with a severity so a human can see exactly what's wrong and why.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from utils.constants import (
    Col,
    DATE_COLUMNS,
    KNOWN_GPS_VALUES,
    KNOWN_VEHICLE_STATUSES,
    NUMERIC_COLUMNS,
    Severity,
)
from utils.helpers import is_blank, parse_date, parse_numeric


@dataclass
class ValidationIssue:
    severity: Severity
    row_index: Optional[int]  # 0-based row index in the source file, None for file-level issues
    column: Optional[str]
    message: str

    def as_dict(self):
        return {
            "severity": self.severity.value,
            "row": self.row_index + 2 if self.row_index is not None else None,  # +2: header row + 1-index
            "column": self.column,
            "message": self.message,
        }


def validate_dataframe(df: pd.DataFrame, missing_required: list[str]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    for col in missing_required:
        issues.append(
            ValidationIssue(
                Severity.ERROR,
                None,
                col,
                f"Required column '{col}' is missing from this file. Rows cannot be safely processed without it.",
            )
        )

    if missing_required:
        # Can't meaningfully validate rows without the required identity columns.
        return issues

    seen_carrier_load: dict[tuple, int] = {}

    for idx, row in df.iterrows():
        carrier = row.get(Col.CARRIER_NUMBER)
        if is_blank(carrier):
            issues.append(ValidationIssue(Severity.ERROR, idx, Col.CARRIER_NUMBER, "Carrier Number is empty."))
        else:
            carrier = str(carrier).strip()

        status = row.get(Col.VEHICLE_STATUS)
        if is_blank(status):
            issues.append(ValidationIssue(Severity.WARNING, idx, Col.VEHICLE_STATUS, "Vehicle Status is empty."))
        elif str(status).strip() not in KNOWN_VEHICLE_STATUSES:
            issues.append(
                ValidationIssue(
                    Severity.INFO,
                    idx,
                    Col.VEHICLE_STATUS,
                    f"Vehicle Status '{status}' is not in the known status list — kept as-is.",
                )
            )

        gps = row.get(Col.GPS_WORKING)
        if not is_blank(gps) and str(gps).strip().title() not in KNOWN_GPS_VALUES:
            issues.append(
                ValidationIssue(
                    Severity.WARNING,
                    idx,
                    Col.GPS_WORKING,
                    f"GPS Working value '{gps}' is not 'Yes'/'No'.",
                )
            )

        if is_blank(row.get(Col.ENTERED_BY_BRANCH)):
            issues.append(
                ValidationIssue(Severity.WARNING, idx, Col.ENTERED_BY_BRANCH, "Entered By Branch is missing — manual branch selection will be required.")
            )

        for date_col in DATE_COLUMNS:
            raw = row.get(date_col)
            if is_blank(raw):
                continue
            parsed = parse_date(raw)
            if parsed is None:
                issues.append(ValidationIssue(Severity.ERROR, idx, date_col, f"'{raw}' is not a recognizable date."))
            elif parsed > dt.date.today() + dt.timedelta(days=1):
                issues.append(ValidationIssue(Severity.INFO, idx, date_col, f"Date {parsed} is in the future — please confirm."))

        for num_col in NUMERIC_COLUMNS:
            raw = row.get(num_col)
            if is_blank(raw):
                continue
            parsed = parse_numeric(raw)
            if parsed is None:
                issues.append(ValidationIssue(Severity.ERROR, idx, num_col, f"'{raw}' is not a valid number."))
            elif parsed < 0:
                issues.append(ValidationIssue(Severity.ERROR, idx, num_col, f"Negative value ({parsed}) is not valid."))

        load_date = parse_date(row.get(Col.LOAD_DATE))
        if carrier and not is_blank(carrier) and load_date:
            key = (str(carrier).strip().lower(), load_date)
            if key in seen_carrier_load:
                issues.append(
                    ValidationIssue(
                        Severity.WARNING,
                        idx,
                        Col.CARRIER_NUMBER,
                        f"Possible duplicate within this file: same Carrier Number and Load Date as row {seen_carrier_load[key] + 2}.",
                    )
                )
            else:
                seen_carrier_load[key] = idx

    return issues


def issues_to_dataframe(issues: list[ValidationIssue]) -> pd.DataFrame:
    if not issues:
        return pd.DataFrame(columns=["severity", "row", "column", "message"])
    return pd.DataFrame([i.as_dict() for i in issues])


def error_row_indices(issues: list[ValidationIssue]) -> set[int]:
    """Rows containing at least one ERROR are excluded from DB insertion."""
    return {i.row_index for i in issues if i.severity == Severity.ERROR and i.row_index is not None}


def summarize_issues(issues: list[ValidationIssue]) -> dict:
    return {
        "errors": sum(1 for i in issues if i.severity == Severity.ERROR),
        "warnings": sum(1 for i in issues if i.severity == Severity.WARNING),
        "info": sum(1 for i in issues if i.severity == Severity.INFO),
    }
