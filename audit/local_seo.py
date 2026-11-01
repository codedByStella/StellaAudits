"""
local_seo.py
Checks for on-page local search signals.

The generic seo.py module covers title, meta description, canonical
tags, and other general SEO factors. This module checks structured
location information, visible contact details, map embeds, and
site identity signals.

Scope note: cross-directory NAP (Name/Address/Phone) consistency
is outside this module. Checks are limited to information available
on the audited page itself.
"""

import re
from urllib.parse import urljoin

from .findings import Finding, CATEGORY_VISITOR

PHONE_PATTERN = re.compile(
    r"(?:\+?\d{1,2}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}"
)

LOCAL_BUSINESS_TYPES = {
    "localbusiness", "restaurant", "store", "autorepair", "dentist", "attorney",
    "medicalbusiness", "professionalservice", "homeandconstructionbusiness",
    "foodestablishment", "hairsalon", "healthandbeautybusiness", "lodgingbusiness",
}


def _extract_ld_json_blocks(soup):
    import json
    blocks = []
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or "")
        except (ValueError, TypeError):
            continue
        if isinstance(data, list):
            blocks.extend(data)
        else:
            blocks.append(data)
    return blocks


def _find_local_business_block(blocks):
    for block in blocks:
        if not isinstance(block, dict):
            continue
        type_val = block.get("@type", "")
        types = [type_val] if isinstance(type_val, str) else (type_val or [])
        if any(str(t).lower() in LOCAL_BUSINESS_TYPES for t in types):
            return block
    return None


def _has_working_favicon_fallback(fetch_result, session) -> bool:
    """
    Checks whether the conventional favicon path serves actual image
    content rather than an HTML fallback response.
    """
    try:
        favicon_url = urljoin(fetch_result.url, "/favicon.ico")
        resp = session.get(favicon_url, timeout=8)
        content_type = resp.headers.get("Content-Type", "")
        return resp.status_code == 200 and content_type.lower().startswith("image/")
    except Exception:
        return False


def run_local_seo_checks(fetch_result, session=None) -> list:
    soup = fetch_result.soup
    findings = []
    visible_text = soup.get_text(separator=" ", strip=True)

    ld_blocks = _extract_ld_json_blocks(soup)
    local_block = _find_local_business_block(ld_blocks)

    if not local_block:
        findings.append(Finding(
            category=CATEGORY_VISITOR,
            severity="Low",
            title="No LocalBusiness structured data found",
            description="No schema.org LocalBusiness or recognized subtype JSON-LD block was found on the page.",
            why_it_matters="Structured location data helps search engines understand the site's location-related information and may support enhanced search results.",
            recommendation="Consider adding an appropriate LocalBusiness JSON-LD block with name, address, telephone, and openingHours.",
        ))
    else:
        missing_fields = [f for f in ("name", "address", "telephone") if not local_block.get(f)]
        if missing_fields:
            findings.append(Finding(
                category=CATEGORY_VISITOR,
                severity="Low",
                title=f"LocalBusiness structured data is missing: {', '.join(missing_fields)}",
                description="A LocalBusiness schema block exists but does not include all expected core fields.",
                why_it_matters="Incomplete structured data may prevent search engines from interpreting important location and contact information.",
                recommendation=f"Consider adding {', '.join(missing_fields)} to the existing LocalBusiness JSON-LD block.",
            ))

        if not local_block.get("openingHours") and not local_block.get("openingHoursSpecification"):
            findings.append(Finding(
                category=CATEGORY_VISITOR,
                severity="Low",
                title="LocalBusiness structured data is missing business hours",
                description="No openingHours or openingHoursSpecification field was found.",
                why_it_matters="Opening hours provide useful location-related information to search engines and visitors.",
                recommendation="Add an openingHours or openingHoursSpecification field to the LocalBusiness JSON-LD block.",
            ))

    has_phone_on_page = bool(PHONE_PATTERN.search(visible_text))
    if not has_phone_on_page:
        findings.append(Finding(
            category=CATEGORY_VISITOR,
            severity="Low",
            title="No phone number found in visible page text",
            description="No recognizable phone number pattern was found in the page's visible text.",
            why_it_matters="Visible contact information makes it easier for visitors to identify available contact methods.",
            recommendation="Display a phone number prominently, such as in the header or footer.",
        ))

    has_maps_embed = any(
        "google.com/maps" in (iframe.get("src") or "")
        for iframe in soup.find_all("iframe")
    )
    if not has_maps_embed:
        findings.append(Finding(
            category=CATEGORY_VISITOR,
            severity="Low",
            title="No embedded Google Map found",
            description="No Google Maps iframe embed was found on the page.",
            why_it_matters="An embedded map provides visitors with a convenient way to view a location.",
            recommendation="Consider embedding a Google Map showing the relevant location.",
        ))

    has_favicon_tag = bool(
        soup.find("link", attrs={"rel": lambda v: v and "icon" in v.lower()})
    )
    has_favicon = (
        has_favicon_tag
        or (
            session is not None
            and _has_working_favicon_fallback(fetch_result, session)
        )
    )

    if not has_favicon:
        findings.append(Finding(
            category=CATEGORY_VISITOR,
            severity="Low",
            title="No favicon found",
            description='No <link rel="icon"> or similar tag was found.',
            why_it_matters="A favicon provides a recognizable icon in browser tabs and bookmarks.",
            recommendation="Add a favicon using the site's available configuration or template.",
        ))

    return findings
