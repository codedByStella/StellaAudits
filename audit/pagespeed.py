"""
pagespeed.py
Optional deeper website analysis using Google's PageSpeed Insights API.

This module supplements the standard audit with information from
a browser-rendered analysis. It is optional and requires an API key.

Without a configured key, this module returns an informational
finding and the remaining audit continues normally.
"""

import requests

from .findings import Finding, CATEGORY_VISITOR

PSI_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
PSI_TIMEOUT = 45


def _skip_finding(reason: str) -> Finding:
    return Finding(
        category=CATEGORY_VISITOR,
        severity="Info",
        title="Deeper detection not run",
        description=reason,
        why_it_matters="Additional browser-rendered analysis was unavailable for this audit. "
                       "The standard audit results are unaffected.",
        recommendation="Configure a PageSpeed Insights API key to enable this optional feature.",
        is_meta=True,
    )


def run_pagespeed_checks(url: str, api_key: str) -> tuple:
    """
    Returns (findings: list, succeeded: bool).
    Indicates whether browser-rendered analysis was available.
    """
    if not api_key:
        return [
            _skip_finding(
                "No PageSpeed Insights API key is configured, so this pass was skipped."
            )
        ], False

    params = {
        "url": url,
        "key": api_key,
        "strategy": "mobile",
        "category": ["accessibility", "performance", "seo"],
    }

    try:
        resp = requests.get(
            PSI_ENDPOINT,
            params=params,
            timeout=PSI_TIMEOUT,
        )
    except requests.RequestException:
        return [
            _skip_finding(
                "The PageSpeed Insights request failed. The rest of the audit is unaffected."
            )
        ], False

    if resp.status_code != 200:
        return [
            _skip_finding(
                f"PageSpeed Insights returned an HTTP error ({resp.status_code})."
            )
        ], False

    try:
        data = resp.json()
        lighthouse = data["lighthouseResult"]
        categories = lighthouse.get("categories", {})
    except (KeyError, ValueError, TypeError):
        return [
            _skip_finding(
                "PageSpeed Insights returned an unexpected response format."
            )
        ], False

    findings = []

    for category_id, label in (
        ("performance", "Performance"),
        ("seo", "SEO"),
    ):
        category = categories.get(category_id)

        if not category or category.get("score") is None:
            continue

        score = round(category["score"] * 100)

        if score < 50:
            findings.append(Finding(
                category=CATEGORY_VISITOR,
                severity="Medium",
                title=f"Lighthouse {label} score is low",
                description=(
                    f"Google's Lighthouse analysis returned a low {label.lower()} score."
                ),
                why_it_matters=(
                    f"The {label.lower()} score indicates potential areas for improvement."
                ),
                recommendation=(
                    "Review the website and identify opportunities for improvement."
                ),
            ))

    return findings, True
