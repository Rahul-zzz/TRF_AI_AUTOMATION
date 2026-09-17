"""Placeholder module for Accounts. Not implemented in Version 0.1.

Deliberately contains no fake data, no fake metrics, and no fake logic.
When this department's real workflow is scoped, its module should follow
the same shape as modules/tracking/ (column_mapping, validation,
processor, alerts, analytics, reports)."""

MODULE_NAME = "Accounts"
STATUS = "Coming Soon — Module Under Development"


def get_status() -> dict:
    return {"module": MODULE_NAME, "status": STATUS, "implemented": False}
