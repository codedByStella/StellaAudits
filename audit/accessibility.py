"""
accessibility.py
Static WCAG 2.1 heuristic checks against the fetched HTML (no headless
browser): missing alt text, unlabeled form fields, missing document
language, heading structure, empty links, duplicate IDs, and similar
markup-level issues.

Checks that require a rendered page are flagged for manual review rather
than guessed at.
"""

from .findings import Finding, CATEGORY_LEGAL


def _has_accessible_label(tag, soup):
    """Check common ways a form field can have an accessible name."""
    if tag.get("aria-label") or tag.get("aria-labelledby"):
        return True
    tag_id = tag.get("id")
    if tag_id:
        label = soup.find("label", attrs={"for": tag_id})
        if label and label.get_text(strip=True):
            return True
    # input wrapped directly inside a <label>
    parent = tag.find_parent("label")
    if parent and parent.get_text(strip=True):
        return True
    if tag.get("title"):
        return True
    if tag.get("placeholder"):
        # placeholder is a weak substitute for a label -- still a real issue,
        # but distinguish it so we don't call it a hard miss below.
        return "placeholder-only"
    return False


def run_accessibility_checks(fetch_result) -> list:
    soup = fetch_result.soup
    findings = []

    # 1. Document language
    html_tag = soup.find("html")
    if not html_tag or not html_tag.get("lang", "").strip():
        findings.append(Finding(
            category=CATEGORY_LEGAL,
            severity="Medium",
            title="Page is missing a declared language (lang attribute)",
            description="The site's HTML doesn't tell browsers or assistive technology what "
                         "language the page is written in.",
            why_it_matters="Screen readers use this to choose the correct pronunciation and voice. "
                            "Without it, visually impaired visitors using a screen reader may hear "
                            "the page read in the wrong language or accent.",
            recommendation='Add lang="en" (or the appropriate language code) to the <html> tag.',
            reference="WCAG 2.1 Success Criterion 3.1.1 (Level A)",
        ))

    # 2. Images missing alt text
    imgs = soup.find_all("img")
    missing_alt = [img for img in imgs if img.get("alt") is None]
    if missing_alt:
        findings.append(Finding(
            category=CATEGORY_LEGAL,
            severity="High",
            title=f"{len(missing_alt)} image(s) missing alt text",
            description="These images have no alt attribute at all, so screen readers announce "
                         "them as an unlabeled image or skip them entirely.",
            why_it_matters="Missing alt text is one of the most common accessibility failures -- "
                            "it directly blocks blind and low-vision visitors from understanding "
                            "page content.",
            recommendation='Add a short, descriptive alt="..." to every meaningful image. '
                            'Purely decorative images should use alt="" (empty, not missing) so '
                            'screen readers skip them cleanly.',
            reference="WCAG 2.1 Success Criterion 1.1.1 (Level A)",
        ))

    # 3. Form fields without an accessible label
    unlabeled, placeholder_only = [], []
    for field in soup.find_all(["input", "textarea", "select"]):
        field_type = (field.get("type") or "").lower()
        if field_type in ("hidden", "submit", "button", "image", "reset"):
            continue
        result = _has_accessible_label(field, soup)
        if result == "placeholder-only":
            placeholder_only.append(field)
        elif not result:
            unlabeled.append(field)

    if unlabeled:
        findings.append(Finding(
            category=CATEGORY_LEGAL,
            severity="High",
            title=f"{len(unlabeled)} form field(s) with no accessible label",
            description="These inputs have no <label>, aria-label, or title a screen reader can "
                         "announce, so a blind visitor can't tell what information the field wants.",
            why_it_matters="Unlabeled form fields (search boxes, contact forms, newsletter signups) "
                            "are a frequent accessibility barrier for screen-reader users.",
            recommendation="Associate every field with a <label for=\"...\"> or add an aria-label.",
            reference="WCAG 2.1 Success Criteria 1.3.1 & 4.1.2 (Level A)",
        ))
    if placeholder_only:
        findings.append(Finding(
            category=CATEGORY_LEGAL,
            severity="Low",
            title=f"{len(placeholder_only)} form field(s) rely on placeholder text instead of a real label",
            description="Placeholder text disappears the moment someone starts typing and isn't "
                         "reliably announced by all assistive technology.",
            why_it_matters="Lower risk than a fully unlabeled field, but still a common accessibility "
                            "audit finding and a real usability problem for older visitors.",
            recommendation="Add a visible or screen-reader-only <label> in addition to the placeholder.",
            reference="WCAG 2.1 Success Criterion 1.3.1 (Level A)",
        ))

    # 4. Heading structure
    headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
    h1s = [h for h in headings if h.name == "h1"]
    if len(h1s) == 0:
        findings.append(Finding(
            category=CATEGORY_LEGAL,
            severity="Medium",
            title="Page has no top-level heading (H1)",
            description="There's no <h1> element, so screen-reader users navigating by heading "
                         "have no clear entry point into the page's content.",
            why_it_matters="Both an accessibility barrier and an SEO weakness.",
            recommendation="Add exactly one <h1> that describes the main content of the page.",
            reference="WCAG 2.1 Success Criterion 1.3.1 (Level A)",
        ))
    elif len(h1s) > 1:
        findings.append(Finding(
            category=CATEGORY_LEGAL,
            severity="Low",
            title=f"Page has {len(h1s)} H1 headings instead of one",
            description="Multiple top-level headings make the page's outline ambiguous for "
                         "screen-reader navigation.",
            why_it_matters="Minor accessibility friction; also dilutes the page's SEO topical focus.",
            recommendation="Use a single H1 per page and structure the rest with H2/H3.",
            reference="WCAG 2.1 Success Criterion 1.3.1 (Level A)",
        ))

    prev_level = 0
    skips = 0
    for h in headings:
        level = int(h.name[1])
        if prev_level and level - prev_level > 1:
            skips += 1
        prev_level = level
    if skips:
        findings.append(Finding(
            category=CATEGORY_LEGAL,
            severity="Low",
            title="Heading levels skip (e.g. H1 straight to H3)",
            description=f"Detected {skips} place(s) where the heading order jumps a level.",
            why_it_matters="Screen-reader users rely on heading levels like a table of contents; "
                            "skipped levels make the page's structure confusing.",
            recommendation="Keep headings in strict order -- don't skip from H1 to H3.",
            reference="WCAG 2.1 Success Criterion 1.3.1 (Level A)",
        ))

    # 5. Page title
    title_tag = soup.find("title")
    if not title_tag or not title_tag.get_text(strip=True):
        findings.append(Finding(
            category=CATEGORY_LEGAL,
            severity="Medium",
            title="Page is missing a <title>",
            description="The browser tab / window title is blank or missing.",
            why_it_matters="Screen-reader users hear the page title first when a page loads -- "
                            "without one, they get no context for where they've landed.",
            recommendation="Add a concise, descriptive <title> to every page.",
            reference="WCAG 2.1 Success Criterion 2.4.2 (Level A)",
        ))

    # 6. Empty links / buttons with no accessible text
    empty_links = []
    for a in soup.find_all("a"):
        text = a.get_text(strip=True)
        has_label = a.get("aria-label") or a.get("title")
        has_img_alt = any(img.get("alt") for img in a.find_all("img"))
        if not text and not has_label and not has_img_alt:
            empty_links.append(a)
    if empty_links:
        findings.append(Finding(
            category=CATEGORY_LEGAL,
            severity="Medium",
            title=f"{len(empty_links)} link(s) with no readable text",
            description="These links have no text, aria-label, or labeled image inside them, so "
                         "a screen reader announces them simply as \"link\" with no destination info.",
            why_it_matters="Common in icon-only nav links (hamburger menus, social icons).",
            recommendation='Add an aria-label (e.g. aria-label="Open menu") to icon-only links.',
            reference="WCAG 2.1 Success Criterion 2.4.4 (Level A)",
        ))

    # 7. Duplicate IDs
    ids = [el.get("id") for el in soup.find_all(attrs={"id": True})]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        findings.append(Finding(
            category=CATEGORY_LEGAL,
            severity="Low",
            title="Duplicate id attribute(s) found",
            description="The same id value is assigned to more than one element.",
            why_it_matters="Duplicate IDs can break aria-labelledby/aria-describedby references and "
                            "confuse assistive technology about which element is being referenced.",
            recommendation="Ensure every id attribute on the page is unique.",
            reference="WCAG 2.1 Success Criterion 4.1.1 (Level A)",
        ))

    # 8. Tables without headers
    for table in soup.find_all("table"):
        if not table.find("th"):
            findings.append(Finding(
                category=CATEGORY_LEGAL,
                severity="Medium",
                title="Data table without header cells",
                description="A <table> was found with no <th> header cells.",
                why_it_matters="Without headers, screen readers can't announce what each column/row "
                                "of data means as a user navigates through it.",
                recommendation="Use <th> for header rows/columns, or scope=\"col\"/\"row\" attributes.",
                reference="WCAG 2.1 Success Criterion 1.3.1 (Level A)",
            ))
            break  # one mention is enough, don't spam per-table

    # 9. iframes without a title
    for iframe in soup.find_all("iframe"):
        if not iframe.get("title"):
            findings.append(Finding(
                category=CATEGORY_LEGAL,
                severity="Low",
                title="Embedded frame (iframe) missing a title",
                description="An <iframe> (e.g. embedded map or video) has no title attribute.",
                why_it_matters="Screen readers announce iframes by their title so a user knows "
                                "what the embedded content is before deciding to explore it.",
                recommendation='Add a descriptive title="..." to each iframe.',
                reference="WCAG 2.1 Success Criterion 4.1.2 (Level A)",
            ))
            break

    # 10. Color contrast -- can't be measured without rendering; always flag as manual step.
    findings.append(Finding(
        category=CATEGORY_LEGAL,
        severity="Info",
        title="Color contrast not automatically verified",
        description="Text/background color contrast requires a rendered page and wasn't measured "
                     "in this automated pass.",
        why_it_matters="Low-contrast text (light gray on white, etc.) is another common WCAG "
                        "failure and worth a manual or tool-assisted check (e.g. WebAIM Contrast "
                        "Checker) before finalizing a report to a client.",
        recommendation="Manually spot-check body text and buttons against WCAG AA contrast ratios "
                        "(4.5:1 normal text, 3:1 large text).",
        reference="WCAG 2.1 Success Criterion 1.4.3 (Level AA)",
        is_meta=True,
    ))

    return findings
