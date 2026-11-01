"""
runner.py
Orchestrates a full audit by coordinating the fetching,
analysis, and reporting modules.
"""

from datetime import datetime, timezone

from .fetcher import fetch_page, new_session, FetchError
from .accessibility import run_accessibility_checks
from .seo import run_seo_checks
from .local_seo import run_local_seo_checks
from .security import run_passive_security_checks
from .pagespeed import run_pagespeed_checks
from .js_detection import detect_js_rendering
from .scoring import compute_score_and_grade
from .findings import Finding, sort_findings, CATEGORY_LEGAL, CATEGORY_VISITOR
import config


class AuditResult:
    def __init__(self, url, findings, generated_at):
        self.url = url
        self.findings = findings
        self.generated_at = generated_at
        self.score, self.grade = compute_score_and_grade(findings)

    def by_category(self, category):
        return sort_findings([
            finding for finding in self.findings
            if finding.category == category
        ])

    def counts_by_severity(self):
        counts = {"High": 0, "Medium": 0, "Low": 0, "Info": 0}

        for finding in self.findings:
            counts[finding.severity] = (
                counts.get(finding.severity, 0) + 1
            )

        return counts


def _js_rendering_notice(js_check: dict) -> Finding:
    return Finding(
        category=CATEGORY_LEGAL,
        severity="Info",
        title="Client-side rendering may affect audit coverage",
        description=(
            "The initial HTML may not contain all content displayed "
            "after the page finishes loading."
        ),
        why_it_matters=(
            "Some findings may require manual verification against "
            "the fully rendered page."
        ),
        recommendation=(
            "Review the affected page in a browser before treating "
            "structural findings as confirmed."
        ),
        is_meta=True,
    )


def run_full_audit(
    raw_url: str,
    include_deeper_detection: bool = True,
) -> AuditResult:

    session = new_session()
    fetch_result = fetch_page(raw_url, session=session)

    findings = []

    findings.extend(run_accessibility_checks(fetch_result))
    findings.extend(run_seo_checks(fetch_result, session))
    findings.extend(run_local_seo_checks(fetch_result, session))
    findings.extend(run_passive_security_checks(fetch_result))

    js_check = detect_js_rendering(fetch_result)

    if include_deeper_detection:
        api_key = config.get("pagespeed_api_key")
        psi_findings, _ = run_pagespeed_checks(
            fetch_result.url,
            api_key,
        )
        findings.extend(psi_findings)

    if js_check["likely_js_rendered"]:
        findings.insert(
            0,
            _js_rendering_notice(js_check),
        )

    return AuditResult(
        url=fetch_result.url,
        findings=findings,
        generated_at=datetime.now(timezone.utc),
    )
