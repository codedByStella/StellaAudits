"""
report.py
Renders an AuditResult into a PDF using xhtml2pdf.
"""

import io
import os
import re
from datetime import datetime

from jinja2 import Environment, FileSystemLoader, select_autoescape
from xhtml2pdf import pisa

from .findings import CATEGORY_LEGAL, CATEGORY_VISITOR, CATEGORY_SECURITY
import config


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")


# Escape externally sourced content before rendering it into the PDF.
_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(enabled_extensions=("html",)),
)


def make_base_filename(url: str) -> str:
    """Creates a filename stem shared by the PDF and email draft."""
    domain = re.sub(r"^https?://", "", url).split("/")[0]
    domain = re.sub(r"[^a-zA-Z0-9.-]", "_", domain)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"audit-{domain}-{stamp}"


def _safe_filename(url: str) -> str:
    return f"{make_base_filename(url)}.pdf"


def render_report_html(audit_result, comparison=None) -> str:
    """
    Renders the audit result into HTML.

    comparison: optional comparison data containing previous audit
    information and finding changes.
    """
    template = _env.get_template("report_pdf.html")

    sections = [
        (CATEGORY_LEGAL, audit_result.by_category(CATEGORY_LEGAL)),
        (CATEGORY_VISITOR, audit_result.by_category(CATEGORY_VISITOR)),
        (CATEGORY_SECURITY, audit_result.by_category(CATEGORY_SECURITY)),
    ]

    return template.render(
        url=audit_result.url,
        generated_at=audit_result.generated_at.strftime("%B %d, %Y %H:%M UTC"),
        counts=audit_result.counts_by_severity(),
        total_findings=len(audit_result.findings),
        score=audit_result.score,
        grade=audit_result.grade,
        sections=sections,
        comparison=comparison,
        brand_name=config.get("brand_name"),
        brand_email=config.get("brand_email"),
        brand_phone=config.get("brand_phone"),
        brand_tagline=config.get("brand_tagline"),
    )


def render_report_pdf_bytes(audit_result, comparison=None) -> bytes:
    html = render_report_html(audit_result, comparison=comparison)
    buffer = io.BytesIO()

    result = pisa.CreatePDF(src=html, dest=buffer)

    if result.err:
        raise RuntimeError("Failed to render PDF report.")

    return buffer.getvalue()


def save_report_pdf(
    audit_result,
    output_dir: str,
    base_filename: str = None,
    comparison=None,
) -> str:
    os.makedirs(output_dir, exist_ok=True)

    stem = base_filename or make_base_filename(audit_result.url)
    filename = f"{stem}.pdf"
    filepath = os.path.join(output_dir, filename)

    pdf_bytes = render_report_pdf_bytes(
        audit_result,
        comparison=comparison,
    )

    with open(filepath, "wb") as f:
        f.write(pdf_bytes)

    return filepath
