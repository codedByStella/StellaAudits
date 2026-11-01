"""
seo.py

Standard SEO and discoverability checks based on publicly
available page content and common discovery resources.

This module performs read-only analysis of fetched page content
and checks standard public paths for crawler guidance and sitemaps.
"""

from .findings import Finding, CATEGORY_VISITOR
from .fetcher import fetch_text


def run_seo_checks(fetch_result, session) -> list:
    soup = fetch_result.soup
    findings = []

    # Title tag
    title_tag = soup.find("title")
    title_text = title_tag.get_text(strip=True) if title_tag else ""

    if not title_text:
        findings.append(Finding(
            category=CATEGORY_VISITOR,
            severity="High",
            title="Missing page title",
            description="No <title> text was found for this page.",
            why_it_matters=(
                "The title tag helps search engines understand the page "
                "and is commonly displayed as the clickable heading "
                "in search results."
            ),
            recommendation=(
                "Add a unique, descriptive title that accurately "
                "summarizes the page."
            ),
        ))

    # Meta description
    meta_desc = soup.find("meta", attrs={"name": "description"})
    desc_text = meta_desc.get("content", "").strip() if meta_desc else ""

    if not desc_text:
        findings.append(Finding(
            category=CATEGORY_VISITOR,
            severity="Medium",
            title="Missing meta description",
            description="No <meta name=\"description\"> tag was found.",
            why_it_matters=(
                "Search engines may generate a result preview from "
                "page content when a meta description is unavailable."
            ),
            recommendation=(
                "Add a concise, descriptive meta description "
                "summarizing the page."
            ),
        ))

    # H1 presence
    h1s = soup.find_all("h1")

    if not h1s:
        findings.append(Finding(
            category=CATEGORY_VISITOR,
            severity="Medium",
            title="No H1 heading for search engines to key off of",
            description="No H1 heading was found on the page.",
            why_it_matters=(
                "A clear primary heading helps communicate "
                "the page's main subject."
            ),
            recommendation=(
                "Add a clear H1 heading that describes the page's content."
            ),
        ))

    # Image alt text
    imgs = soup.find_all("img")
    missing_alt = [
        img for img in imgs
        if img.get("alt") is None or not img.get("alt").strip()
    ]

    if imgs and len(missing_alt) == len(imgs):
        findings.append(Finding(
            category=CATEGORY_VISITOR,
            severity="Low",
            title="No images have descriptive alt text",
            description=(
                "Images on the page lack meaningful alternative text."
            ),
            why_it_matters=(
                "Alternative text helps search engines interpret "
                "images and provides additional context about page content."
            ),
            recommendation=(
                "Add descriptive alternative text to relevant images."
            ),
        ))

    # Canonical tag
    canonical = soup.find("link", attrs={"rel": "canonical"})

    if not canonical:
        findings.append(Finding(
            category=CATEGORY_VISITOR,
            severity="Low",
            title="Missing canonical tag",
            description="No <link rel=\"canonical\"> was found.",
            why_it_matters=(
                "Canonical links help search engines identify the "
                "preferred URL when similar content is available "
                "through multiple addresses."
            ),
            recommendation=(
                "Add an appropriate canonical link to the page."
            ),
        ))

    # Viewport / mobile-friendliness
    viewport = soup.find("meta", attrs={"name": "viewport"})

    if not viewport:
        findings.append(Finding(
            category=CATEGORY_VISITOR,
            severity="High",
            title="Missing mobile viewport tag",
            description="No <meta name=\"viewport\"> tag was found.",
            why_it_matters=(
                "Without viewport configuration, pages may not "
                "display correctly on mobile devices."
            ),
            recommendation=(
                'Add <meta name="viewport" '
                'content="width=device-width, initial-scale=1">.'
            ),
        ))

    # Structured data
    ld_json = soup.find_all(
        "script",
        attrs={"type": "application/ld+json"},
    )

    if not ld_json:
        findings.append(Finding(
            category=CATEGORY_VISITOR,
            severity="Low",
            title="No structured data (schema.org) found",
            description=(
                "No JSON-LD structured data blocks were detected."
            ),
            why_it_matters=(
                "Structured data provides search engines with "
                "additional information about page content."
            ),
            recommendation=(
                "Consider adding relevant JSON-LD structured data."
            ),
        ))

    # HTTPS
    if not fetch_result.is_https:
        findings.append(Finding(
            category=CATEGORY_VISITOR,
            severity="High",
            title="Site is not served over HTTPS",
            description="The page loaded over plain HTTP.",
            why_it_matters=(
                "HTTPS protects connections and is a recognized "
                "search ranking consideration. Browsers may also "
                "warn visitors about unsecured pages."
            ),
            recommendation=(
                "Configure an SSL/TLS certificate and redirect "
                "HTTP traffic to HTTPS."
            ),
        ))

    # robots.txt
    status, text = fetch_text(
        session,
        fetch_result.url,
        "/robots.txt",
    )

    if status is None or status >= 400:
        findings.append(Finding(
            category=CATEGORY_VISITOR,
            severity="Info",
            title="No robots.txt found",
            description=(
                "/robots.txt did not return a valid response."
            ),
            why_it_matters=(
                "A robots.txt file can provide search engine crawlers "
                "with guidance about site access."
            ),
            recommendation=(
                "Consider adding a robots.txt file with appropriate "
                "crawler guidance."
            ),
        ))

    elif text and "disallow: /" in text.lower().replace(" ", ""):
        findings.append(Finding(
            category=CATEGORY_VISITOR,
            severity="High",
            title="robots.txt is blocking the entire site from search engines",
            description=(
                "robots.txt contains a blanket \"Disallow: /\" rule."
            ),
            why_it_matters=(
                "This directive tells compliant crawlers not to "
                "access pages on the site."
            ),
            recommendation=(
                "Review the directive and remove it if site-wide "
                "crawler blocking is unintended."
            ),
        ))

    # sitemap.xml
    status, _ = fetch_text(
        session,
        fetch_result.url,
        "/sitemap.xml",
    )

    if status is None or status >= 400:
        findings.append(Finding(
            category=CATEGORY_VISITOR,
            severity="Low",
            title="No sitemap.xml found",
            description=(
                "/sitemap.xml did not return a valid response."
            ),
            why_it_matters=(
                "A sitemap can help search engines discover "
                "pages across a website."
            ),
            recommendation=(
                "Consider generating and publishing an XML sitemap."
            ),
        ))

    return findings
