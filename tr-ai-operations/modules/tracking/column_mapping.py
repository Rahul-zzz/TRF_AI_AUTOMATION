"""
Maps varying spreadsheet header spellings onto the canonical internal
column names in utils.constants.Col.

Unknown columns are NEVER silently discarded — they are kept (prefixed)
and reported so a human can decide whether the mapping list needs
extending.
"""

from __future__ import annotations

import pandas as pd

from utils.constants import Col, REQUIRED_COLUMNS
from utils.helpers import normalize_header

# Each canonical column maps to a set of normalized header variants that
# should resolve to it. normalize_header() lower-cases, strips punctuation
# and collapses whitespace, so "Carrier No.", "carrier_no", "Carrier  No"
# all normalize to "carrier no" and match here.
COLUMN_ALIASES: dict[str, list[str]] = {
    Col.SL_NO: ["sl no", "s no", "serial no", "sr no"],
    Col.CARRIER_NUMBER: ["carrier number", "carrier no", "vehicle number", "vehicle no", "truck number"],
    Col.VEHICLE_CATEGORY: ["vehicle category", "vehicle type", "category"],
    Col.RUNNING_ROUTE: ["running route", "route"],
    Col.YTD_GRADE: ["ytd grade", "grade"],
    Col.CONSIGNER: ["consigner", "consignor"],
    Col.LOAD_DATE: ["load date", "loading date"],
    Col.EXIT_DATE: ["exit date"],
    Col.DISPATCH_DATE: ["dispatch date"],
    Col.DAYS_AT_LOCATION: ["days at location", "days at location "],
    Col.FROM_CITY: ["from city", "origin city", "from"],
    Col.TO_CITY_1: ["to city first", "to city 1", "to city"],
    Col.TO_CITY_2: ["to city second", "to city 2"],
    Col.TO_CITY_3: ["to city third", "to city 3"],
    Col.EXPECTED_UNLOADING_DATE: ["expected unloading date"],
    Col.ACTUAL_UNLOADING_DATE: ["actual unloading date"],
    Col.NEXT_LOADING_POINT_REACH_DATE: ["next loading point reach date", "next loading point reach"],
    Col.DAYS_IN_TRANSIT: ["days in transit"],
    Col.CURRENT_LOCATION: ["current location"],
    Col.STATE: ["state"],
    Col.NEXT_LOADING_STATION: ["next loading station"],
    Col.VEHICLE_STATUS: ["vehicle status", "status"],
    Col.DATE_OF_CURRENT_STATUS: ["date of current status", "status date"],
    Col.GPS_WORKING: ["gps working", "gps status", "gps"],
    Col.ENTERED_BY_BRANCH: ["entered by branch", "branch", "entered branch"],
    Col.REMARKS: ["remarks", "remark", "comments", "notes"],
}

# Reverse lookup: normalized variant -> canonical column
_VARIANT_TO_CANONICAL: dict[str, str] = {}
for canonical, variants in COLUMN_ALIASES.items():
    _VARIANT_TO_CANONICAL[normalize_header(canonical)] = canonical
    for variant in variants:
        _VARIANT_TO_CANONICAL[normalize_header(variant)] = canonical


class ColumnMappingResult:
    def __init__(self, dataframe: pd.DataFrame, missing_required: list[str], unmapped_columns: list[str]):
        self.dataframe = dataframe
        self.missing_required = missing_required
        self.unmapped_columns = unmapped_columns

    @property
    def is_usable(self) -> bool:
        """A file is usable if at least the required identity columns are present."""
        return len(self.missing_required) == 0


def normalize_columns(df: pd.DataFrame) -> ColumnMappingResult:
    """Rename columns in df to canonical names where a match is found.
    Columns that cannot be matched are kept, untouched, with an
    'unmapped__' prefix so no data is silently dropped."""
    rename_map: dict[str, str] = {}
    unmapped: list[str] = []

    for original_col in df.columns:
        key = normalize_header(original_col)
        canonical = _VARIANT_TO_CANONICAL.get(key)
        if canonical:
            rename_map[original_col] = canonical
        else:
            unmapped.append(str(original_col))

    renamed = df.rename(columns=rename_map)

    # Handle duplicate canonical targets (e.g. two columns both map to the
    # same canonical name) by keeping the first and reporting the rest as
    # unmapped so nothing is silently overwritten.
    seen: set[str] = set()
    final_columns = []
    for col in renamed.columns:
        if col in COLUMN_ALIASES and col in seen:
            unmapped.append(f"{col} (duplicate source column)")
            final_columns.append(f"unmapped__duplicate__{col}")
        else:
            if col in COLUMN_ALIASES:
                seen.add(col)
            final_columns.append(col)
    renamed.columns = final_columns

    missing_required = [c for c in REQUIRED_COLUMNS if c not in renamed.columns]

    return ColumnMappingResult(dataframe=renamed, missing_required=missing_required, unmapped_columns=unmapped)
