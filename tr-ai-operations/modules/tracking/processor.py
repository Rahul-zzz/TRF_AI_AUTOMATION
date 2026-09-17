"""
Orchestrates the upload -> normalize -> validate -> branch-detect ->
consolidate -> store pipeline for one or more uploaded Excel files.

This module has no Streamlit imports so it is fully unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from config.settings import SETTINGS
from database.operations import (
    create_upload_batch,
    find_possible_duplicate,
    get_or_create_branch,
    insert_tracking_record,
)
from modules.tracking.column_mapping import normalize_columns
from modules.tracking.validation import error_row_indices, summarize_issues, validate_dataframe, ValidationIssue
from utils.constants import Col, DATE_COLUMNS, NUMERIC_COLUMNS, Severity
from utils.helpers import is_blank, parse_date, parse_numeric


@dataclass
class FileProcessResult:
    filename: str
    detected_branch: Optional[str]
    branch_confidence: str  # "detected" | "manual_required" | "manual_override"
    total_rows: int
    inserted_rows: int
    skipped_rows: int
    possible_duplicates: int
    issues: list[ValidationIssue] = field(default_factory=list)
    status: str = "FAILED"  # SUCCESS / PARTIAL / FAILED
    error: Optional[str] = None


def detect_branch_name(df: pd.DataFrame) -> Optional[str]:
    if Col.ENTERED_BY_BRANCH not in df.columns:
        return None
    values = df[Col.ENTERED_BY_BRANCH].dropna().astype(str).str.strip()
    values = values[values != ""]
    if values.empty:
        return None
    mode = values.mode()
    return mode.iloc[0] if not mode.empty else None


def _row_to_typed_dict(row: pd.Series) -> dict:
    out = {}
    for col in row.index:
        value = row[col]
        if col in DATE_COLUMNS:
            out[col] = parse_date(value)
        elif col in NUMERIC_COLUMNS:
            parsed = parse_numeric(value)
            out[col] = int(parsed) if parsed is not None else None
        elif is_blank(value):
            out[col] = None
        else:
            out[col] = str(value).strip()
    return out


def read_excel_file(file_obj_or_path) -> pd.DataFrame:
    return pd.read_excel(file_obj_or_path, dtype=object)


def process_file(
    session: Session,
    filename: str,
    df: pd.DataFrame,
    manual_branch: Optional[str] = None,
    is_synthetic: bool = False,
) -> FileProcessResult:
    """Process a single already-loaded dataframe (one Excel file's contents)."""
    try:
        mapping_result = normalize_columns(df)
    except Exception as exc:  # pragma: no cover - defensive
        return FileProcessResult(
            filename=filename,
            detected_branch=None,
            branch_confidence="manual_required",
            total_rows=0,
            inserted_rows=0,
            skipped_rows=0,
            possible_duplicates=0,
            status="FAILED",
            error=f"Could not read file structure: {exc}",
        )

    normalized_df = mapping_result.dataframe
    issues = validate_dataframe(normalized_df, mapping_result.missing_required)

    if not mapping_result.is_usable:
        return FileProcessResult(
            filename=filename,
            detected_branch=manual_branch,
            branch_confidence="manual_required",
            total_rows=len(df),
            inserted_rows=0,
            skipped_rows=len(df),
            possible_duplicates=0,
            issues=issues,
            status="FAILED",
            error="Missing required columns — see validation issues.",
        )

    detected = detect_branch_name(normalized_df)
    branch_name = manual_branch or detected
    branch_confidence = "manual_override" if manual_branch else ("detected" if detected else "manual_required")

    if not branch_name:
        return FileProcessResult(
            filename=filename,
            detected_branch=None,
            branch_confidence="manual_required",
            total_rows=len(df),
            inserted_rows=0,
            skipped_rows=len(df),
            possible_duplicates=0,
            issues=issues,
            status="FAILED",
            error="Branch could not be detected and no manual branch was supplied.",
        )

    branch = get_or_create_branch(session, branch_name)
    batch = create_upload_batch(session, source_filename=filename, branch=branch, is_synthetic=is_synthetic)

    bad_rows = error_row_indices(issues)
    inserted = 0
    duplicates = 0
    threshold_days = SETTINGS.thresholds.DUPLICATE_WINDOW_DAYS

    for idx, row in normalized_df.iterrows():
        if idx in bad_rows:
            continue
        typed_row = _row_to_typed_dict(row)
        if is_blank(typed_row.get(Col.CARRIER_NUMBER)):
            continue

        dup = find_possible_duplicate(
            session,
            carrier_number=typed_row[Col.CARRIER_NUMBER],
            load_date=typed_row.get(Col.LOAD_DATE),
            branch_id=branch.id,
            window_days=threshold_days,
        )
        if dup is not None:
            duplicates += 1
            issues.append(
                ValidationIssue(
                    severity=Severity.WARNING,
                    row_index=idx,
                    column=Col.CARRIER_NUMBER,
                    message="Possible duplicate of an existing record (vehicle already has a tracking entry near this Load Date). Inserted anyway — historical data is never overwritten.",
                )
            )

        insert_tracking_record(session, batch, branch, typed_row)
        inserted += 1

    batch.row_count = inserted
    batch.error_count = len(bad_rows)
    batch.status = "SUCCESS" if inserted and not bad_rows else ("PARTIAL" if inserted else "FAILED")
    session.flush()

    return FileProcessResult(
        filename=filename,
        detected_branch=branch_name,
        branch_confidence=branch_confidence,
        total_rows=len(df),
        inserted_rows=inserted,
        skipped_rows=len(df) - inserted,
        possible_duplicates=duplicates,
        issues=issues,
        status=batch.status,
        error=None,
    )


def process_multiple_files(
    session: Session,
    files: list[tuple[str, pd.DataFrame]],
    manual_branch_overrides: Optional[dict[str, str]] = None,
    is_synthetic: bool = False,
) -> list[FileProcessResult]:
    manual_branch_overrides = manual_branch_overrides or {}
    results = []
    for filename, df in files:
        result = process_file(
            session,
            filename,
            df,
            manual_branch=manual_branch_overrides.get(filename),
            is_synthetic=is_synthetic,
        )
        results.append(result)
    return results
