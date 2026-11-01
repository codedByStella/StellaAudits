"""
findings.py

Shared data model for audit findings.

This module defines the common structure used by the application's
analysis, reporting, and data-management components.

Proprietary finding-identification and comparison logic has been
intentionally redacted from this public portfolio version.
"""

from dataclasses import dataclass

SEVERITY_ORDER = {
    "High": 0,
    "Medium": 1,
    "Low": 2,
    "Info": 3,
}

CATEGORY_LEGAL = "Legal Risk (ADA / Accessibility)"
CATEGORY_VISITOR = "Visitor Risk (SEO & Structure)"
CATEGORY_SECURITY = "Security & Liability Risk"


@dataclass
class Finding:
    category: str
    severity: str
    title: str
    description: str
    why_it_matters: str
    recommendation: str
    reference: str = ""
    evidence: str = ""
    is_meta: bool = False

    def severity_rank(self):
        return SEVERITY_ORDER.get(self.severity, 99)

    @property
    def check_key(self) -> str:
        """
        Proprietary finding-identification logic is redacted.
        """
        raise NotImplementedError(
            "Finding identification is intentionally redacted "
            "in this public portfolio version."
        )


def sort_findings(findings):
    return sorted(
        findings,
        key=lambda finding: (
            finding.severity_rank(),
            finding.category,
        ),
    )
