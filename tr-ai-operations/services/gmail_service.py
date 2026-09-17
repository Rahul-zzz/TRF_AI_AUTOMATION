"""
Future Gmail report-retrieval architecture. NOT implemented in Version 0.1.

Planned future flow (once a Gmail connector / OAuth client is set up):

    Gmail
      -> Authorized OAuth access (never a stored password)
      -> Identify branch report emails (sender/subject rules, TBD)
      -> Download Excel attachment
      -> Validate (modules.tracking.validation)
      -> Process (modules.tracking.processor)
      -> Store (database.operations)

This file intentionally raises NotImplementedError rather than silently
doing nothing or pretending to connect, so callers can't mistake this
for a working integration.
"""

from __future__ import annotations


class GmailService:
    is_connected: bool = False

    def fetch_branch_reports(self, since_date=None):
        raise NotImplementedError(
            "Gmail integration is not implemented in this version. "
            "No OAuth client is configured and no Gmail credentials are stored."
        )

    def authorize(self):
        raise NotImplementedError(
            "Gmail OAuth authorization is not implemented. This service will "
            "never request or store a Gmail password."
        )


gmail_service = GmailService()
