"""Export helpers: dataframes -> Excel/CSV bytes, and a simple PDF for the
Daily Review. Excel/CSV are the primary, always-available export paths;
PDF is best-effort via reportlab."""

from __future__ import annotations

import io

import pandas as pd


def dataframe_to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Sheet1") -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return buffer.getvalue()


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def daily_review_to_pdf_bytes(review: dict) -> bytes:
    """Render the Daily Review dict as a simple, readable PDF."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 2 * cm

    def line(text, size=10, bold=False, gap=0.55 * cm):
        nonlocal y
        if y < 2 * cm:
            c.showPage()
            y = height - 2 * cm
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawString(2 * cm, y, text[:110])
        y -= gap

    line("TR DAILY TRACKING REVIEW", size=16, bold=True, gap=0.9 * cm)
    line(f"Date: {review.get('review_date')}", bold=True)
    line("")

    line("Report Status", bold=True, size=12)
    rs = review.get("report_status", {})
    for k, v in rs.items():
        line(f"  {k.replace('_', ' ').title()}: {v}")
    line("")

    line("Operational Summary", bold=True, size=12)
    op = review.get("operational_summary", {})
    for k, v in op.items():
        line(f"  {k.replace('_', ' ').title()}: {v}")
    line("")

    line("Critical Issues", bold=True, size=12)
    critical = review.get("critical_issues", [])
    if not critical:
        line("  None.")
    for item in critical[:30]:
        line(f"  - {item}")
    line("")

    line("High Priority Issues", bold=True, size=12)
    high = review.get("high_priority_issues", [])
    if not high:
        line("  None.")
    for item in high[:30]:
        line(f"  - {item}")
    line("")

    line("Branch Summary", bold=True, size=12)
    for row in review.get("branch_summary", []):
        line(f"  {row}")
    line("")

    line("Recommended Follow-up", bold=True, size=12)
    for item in review.get("recommended_follow_up", []):
        line(f"  - {item}")

    c.showPage()
    c.save()
    return buffer.getvalue()
