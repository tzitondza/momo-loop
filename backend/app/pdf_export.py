"""Generate PDF reports for ranked MoMo Loop opportunities."""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from typing import Any

from fpdf import FPDF


def _ascii(text: Any) -> str:
    raw = str(text or "")
    return (
        raw.replace("—", "-")
        .replace("–", "-")
        .replace("·", "|")
        .replace("×", "x")
        .encode("latin-1", "replace")
        .decode("latin-1")
    )


class OpportunityReport(FPDF):
    def header(self) -> None:
        self.set_font("Helvetica", "B", 14)
        self.cell(
            0,
            8,
            "MoMo Loop - Opportunity Ranking Report",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.set_font("Helvetica", "", 9)
        self.set_text_color(90, 90, 90)
        self.cell(
            0,
            6,
            "Merchant acceptance intelligence | estimated recoverable value for planning",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"Page {self.page_no()}/{{nb}}", align="C")


def build_opportunities_pdf(payload: dict[str, Any]) -> bytes:
    rows = payload.get("opportunities") or []
    scope = payload.get("scope") or {}
    scoring = payload.get("scoring") or {}

    pdf = OpportunityReport(orientation="L", unit="mm", format="A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, _ascii(f"Scope: {scope.get('region', 'South Africa')}"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Generated: {generated}", new_x="LMARGIN", new_y="NEXT")
    if scope.get("last_refreshed"):
        pdf.cell(
            0,
            6,
            _ascii(f"Data last refreshed: {scope['last_refreshed']}"),
            new_x="LMARGIN",
            new_y="NEXT",
        )
    pdf.ln(2)

    headers = [
        ("#", 10),
        ("Location", 48),
        ("Region", 30),
        ("Category", 32),
        ("Score", 16),
        ("Boundary R", 28),
        ("Recoverable R", 30),
        ("Customers", 22),
        ("Gap %", 16),
    ]
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(255, 204, 0)
    for label, width in headers:
        pdf.cell(width, 8, label, border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    for row in rows:
        values = [
            str(row.get("rank", "")),
            _ascii(row.get("location_name", ""))[:28],
            _ascii(row.get("region", ""))[:16],
            _ascii(row.get("merchant_category", ""))[:18],
            f"{row.get('opportunity_score', 0):.1f}",
            f"{float(row.get('boundary_value', 0)):.0f}",
            f"{float(row.get('estimated_recoverable', 0)):.0f}",
            str(row.get("affected_customers", 0)),
            f"{float(row.get('acceptance_gap', 0)) * 100:.0f}",
        ]
        for value, (_, width) in zip(values, headers):
            pdf.cell(width, 7, _ascii(value), border=1)
        pdf.ln()

    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    note = scoring.get("note") or (
        "Scores use transparent business rules. Rapid cash-out after inflow indicates a probable acceptance boundary."
    )
    pdf.multi_cell(0, 5, _ascii(note))

    buffer = BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()
