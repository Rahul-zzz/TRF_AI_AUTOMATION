"""
Future AI Assistant interface.

IMPORTANT: No paid AI API is connected in Version 0.1. Nothing in this
file pretends to be a real LLM. Calling any method below returns a
clearly-labeled "not implemented" response rather than a fabricated
answer, so the UI never displays fake AI output.

When a real model is integrated later, implement each method to call
out to it (e.g. the Anthropic API) and keep this same interface so the
rest of the app (pages/, modules/) doesn't need to change.
"""

from __future__ import annotations

NOT_CONNECTED_MESSAGE = (
    "AI Assistant — Integration Pending. This prototype does not call any "
    "external AI model yet; no answer is fabricated here."
)


class AIService:
    """Prototype Assistant interface. All methods are stubs."""

    is_connected: bool = False

    def ask_question(self, question: str) -> str:
        return NOT_CONNECTED_MESSAGE

    def summarize_tracking(self, kpis: dict) -> str:
        return NOT_CONNECTED_MESSAGE

    def get_branch_alerts(self, branch: str) -> str:
        return NOT_CONNECTED_MESSAGE

    def get_vehicle_status(self, carrier_number: str) -> str:
        return NOT_CONNECTED_MESSAGE

    def get_critical_alerts(self) -> str:
        return NOT_CONNECTED_MESSAGE

    def get_delayed_vehicles(self) -> str:
        return NOT_CONNECTED_MESSAGE

    def explain_alert(self, alert_message: str) -> str:
        return NOT_CONNECTED_MESSAGE

    def generate_daily_review(self, review_data: dict) -> str:
        return NOT_CONNECTED_MESSAGE

    def analyze_branch(self, branch: str) -> str:
        return NOT_CONNECTED_MESSAGE

    def analyze_vehicle(self, carrier_number: str) -> str:
        return NOT_CONNECTED_MESSAGE


ai_service = AIService()
