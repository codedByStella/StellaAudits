"""
outreach.py
Generates a draft outreach email or letter to accompany an audit PDF.

This produces a DRAFT ONLY. Messages are never sent automatically.
A human reviews and personalizes every message before sending.
"""

from .findings import sort_findings, CATEGORY_LEGAL, CATEGORY_VISITOR, CATEGORY_SECURITY


def _top_findings_summary(findings, limit=3):
    """
    Selects representative findings for the draft summary.
    Audit metadata notices are excluded, and findings are prioritized
    across categories to avoid repetitive summaries.
    """
    real = [
        f for f in sort_findings(findings)
        if not f.is_meta and f.severity != "Info"
    ]

    if not real:
        return []

    category_order = [CATEGORY_LEGAL, CATEGORY_VISITOR, CATEGORY_SECURITY]
    picked = []

    for category in category_order:
        match = next((f for f in real if f.category == category), None)
        if match:
            picked.append(match)

        if len(picked) >= limit:
            break

    if len(picked) < limit:
        for finding in real:
            if finding not in picked:
                picked.append(finding)

            if len(picked) >= limit:
                break

    return picked[:limit]


def build_email_draft(audit_result, config_get) -> dict:
    """
    config_get: a callable like config.get, injected so this module
    has no hard import-order dependency on config.py.

    Returns the subject, body, and any preparation warnings.
    """
    brand_name = config_get("brand_name")
    brand_email = config_get("brand_email")
    brand_phone = config_get("brand_phone")
    mailing_address = (config_get("brand_mailing_address") or "").strip()

    domain = audit_result.url.split("//")[-1].split("/")[0]
    top_findings = _top_findings_summary(audit_result.findings)

    subject = (
        f"Website audit findings for {domain} "
        f"({audit_result.grade}, {audit_result.score}/100)"
    )

    if top_findings:
        bullet_lines = "\n".join(f"  - {f.title}" for f in top_findings)
        findings_intro = "A few things stood out:"
    else:
        bullet_lines = "  - Nothing major stood out -- solid baseline overall."
        findings_intro = ""

    address_line = mailing_address or "[Add mailing address before sending]"

    body = f"""Hi there,

I ran an independent automated website audit on {domain}, covering accessibility, \
search visibility, and general site quality. It came back with a health score of \
{audit_result.score}/100 ({audit_result.grade}). {findings_intro}

{bullet_lines}

The full report is attached, with explanations and recommended fixes for each \
item. No obligation -- happy to help prioritize or address any of it if useful, \
or simply provide the report for your own review.

{brand_name}
{brand_email} | {brand_phone}

---
This is a promotional message from {brand_name}, sent because {domain} was included \
in an independent website review.

{brand_name}
{address_line}

Don't want to hear from us again? Just reply to this email with "unsubscribe" \
and you won't be contacted again.
"""

    warnings = []

    if not mailing_address:
        warnings.append(
            "A mailing address has not been configured. Review the draft before sending."
        )

    return {
        "subject": subject,
        "body": body,
        "warnings": warnings,
    }


def save_email_draft(audit_result, config_get, output_dir, base_filename) -> str:
    """base_filename: filename stem shared with the PDF (no extension)."""
    import os

    draft = build_email_draft(audit_result, config_get)
    filename = f"{base_filename}-email.txt"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        if draft["warnings"]:
            f.write("=== NOT READY TO SEND ===\n")
            for warning in draft["warnings"]:
                f.write(f"! {warning}\n")
            f.write("=========================\n\n")

        f.write(f"Subject: {draft['subject']}\n\n")
        f.write(draft["body"])

    return filename
