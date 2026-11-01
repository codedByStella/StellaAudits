"""
config.py
Loads user-editable settings from config.json in the project root. Kept as
plain JSON (not code) so non-developers can edit it directly, and separate
from the source files so credentials and personal settings can be excluded
from version control.

If config.json doesn't exist yet, one is created with empty/default values
the first time the app runs.
"""

import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

DEFAULTS = {
    # Get a free key at https://developers.google.com/speed/docs/insights/v5/get-started
    # (click "Get a Key"). Leave blank to skip the optional deeper detection
    # pass -- the rest of the audit works without it.
    "pagespeed_api_key": "",

    # Branding shown on the PDF report's cover and closing pages.
    "brand_name": "Your Brand",
    "brand_email": "you@example.com",
    "brand_phone": "(555) 555-0100",
    "brand_tagline": "Your tagline here",

    # Physical mailing address used by the outreach email drafts. Drafts are
    # marked as not ready to send until this is filled in.
    "brand_mailing_address": "",
}


def _load_or_create():
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w") as f:
            json.dump(DEFAULTS, f, indent=2)
        return dict(DEFAULTS)

    with open(CONFIG_PATH, "r") as f:
        data = json.load(f)

    # Backfill any keys added in newer versions of the tool without
    # clobbering values the user has already customized.
    changed = False
    for key, value in DEFAULTS.items():
        if key not in data:
            data[key] = value
            changed = True
    if changed:
        with open(CONFIG_PATH, "w") as f:
            json.dump(data, f, indent=2)

    return data


_config = _load_or_create()


def get(key):
    return _config.get(key, DEFAULTS.get(key))


def reload():
    global _config
    _config = _load_or_create()
    return _config
