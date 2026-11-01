"""
js_detection.py
Detects when a page may rely on client-side rendering so the audit
pipeline can account for limitations in static HTML analysis.

Static checks parse the HTML as received from the server, before
JavaScript executes. Pages with substantial client-side rendering
may initially contain very little visible content, which can lead
to misleading findings.

This is a heuristic, not a certainty. Results indicate when a page
may warrant additional review rather than claiming definitive proof.
"""

MIN_TEXT_LEN_LOW_CONFIDENCE = 600
MIN_TEXT_LEN_HIGH_CONFIDENCE = 250


def detect_js_rendering(fetch_result) -> dict:
    soup = fetch_result.soup

    visible_text = soup.get_text(separator=" ", strip=True)
    text_len = len(visible_text)

    if text_len < MIN_TEXT_LEN_HIGH_CONFIDENCE:
        return {
            "likely_js_rendered": True,
            "confidence": "medium",
            "reason": "Very little visible text was present in the initial HTML.",
        }

    if text_len < MIN_TEXT_LEN_LOW_CONFIDENCE:
        return {
            "likely_js_rendered": True,
            "confidence": "low",
            "reason": "Visible text was limited in the initial HTML.",
        }

    return {
        "likely_js_rendered": False,
        "confidence": "n/a",
        "reason": "",
    }
