import pandas as pd

from modules.tracking.column_mapping import normalize_columns
from utils.constants import Col


def test_maps_known_variants():
    df = pd.DataFrame(
        {
            "Carrier No.": ["TN01AB1234"],
            "Vehicle Type": ["Car Carrier"],
            "Status": ["In Transit"],
            "GPS": ["Yes"],
            "Branch": ["Chennai"],
        }
    )
    result = normalize_columns(df)
    assert Col.CARRIER_NUMBER in result.dataframe.columns
    assert Col.VEHICLE_CATEGORY in result.dataframe.columns
    assert Col.VEHICLE_STATUS in result.dataframe.columns
    assert Col.GPS_WORKING in result.dataframe.columns
    assert Col.ENTERED_BY_BRANCH in result.dataframe.columns
    assert result.is_usable


def test_missing_required_column_is_reported():
    df = pd.DataFrame({"Some Unrelated Column": [1, 2]})
    result = normalize_columns(df)
    assert Col.CARRIER_NUMBER in result.missing_required
    assert not result.is_usable


def test_unmapped_columns_are_kept_not_dropped():
    df = pd.DataFrame(
        {
            "Carrier Number": ["TN01AB1234"],
            "Vehicle Category": ["Car Carrier"],
            "Vehicle Status": ["In Transit"],
            "Some Weird Extra Field": ["xyz"],
        }
    )
    result = normalize_columns(df)
    assert "Some Weird Extra Field" in result.unmapped_columns
    assert "Some Weird Extra Field" in result.dataframe.columns
