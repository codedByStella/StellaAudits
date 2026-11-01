"""
fetcher.py
Handles all outbound HTTP requests for the audit tool.

Design intent: every request this tool makes is a normal, publicly-invited
request -- the same kind any visitor's browser or a search engine crawler
would make. No authentication bypass, no credential guessing, no requests
to non-public endpoints. Identifies itself with a clear, honest User-Agent
so a site owner who checks their logs can see exactly what hit them and why.
"""

import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

USER_AGENT = (
    "WebsiteAuditBot/1.0 "
    "(+automated website audit)"
)

DEFAULT_TIMEOUT = 15


class FetchError(Exception):
    """Raised when the target site can't be reached or returns an unusable response."""
    pass


class FetchResult:
    def __init__(self, url, status_code, headers, html, soup, elapsed_ms):
        self.url = url
        self.status_code = status_code
        self.headers = headers
        self.html = html
        self.soup = soup
        self.elapsed_ms = elapsed_ms

    @property
    def is_https(self):
        return urlparse(self.url).scheme == "https"

    @property
    def domain(self):
        return urlparse(self.url).netloc


def normalize_url(raw_url: str) -> str:
    url = raw_url.strip()
    if not url:
        raise FetchError("No URL provided.")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def new_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def fetch_page(url: str, session: requests.Session = None, timeout: int = DEFAULT_TIMEOUT) -> FetchResult:
    """Fetch and parse the main HTML page. Raises FetchError on failure."""
    url = normalize_url(url)
    session = session or new_session()

    try:
        resp = session.get(url, timeout=timeout, allow_redirects=True)
    except requests.exceptions.SSLError:
        raise FetchError(f"SSL/certificate error connecting to {url}. The site's certificate "
                          f"may be invalid or expired.")
    except requests.exceptions.ConnectionError:
        raise FetchError(f"Could not connect to {url}. Double-check the URL is correct and the "
                          f"site is online.")
    except requests.exceptions.Timeout:
        raise FetchError(f"Connection to {url} timed out after {timeout}s. The site may be slow "
                          f"or blocking automated requests.")
    except requests.exceptions.RequestException:
        raise FetchError(f"Request to {url} failed. Double-check the URL and try again.")

    if resp.status_code >= 400:
        raise FetchError(f"{url} returned HTTP {resp.status_code} — site may be down or blocking automated requests.")

    elapsed_ms = resp.elapsed.total_seconds() * 1000
    soup = BeautifulSoup(resp.text, "html.parser")
    return FetchResult(resp.url, resp.status_code, resp.headers, resp.text, soup, elapsed_ms)


def fetch_text(session: requests.Session, base_url: str, path: str, timeout: int = 10):
    """
    Best-effort fetch of a supporting public resource (robots.txt, sitemap.xml).
    Returns (status_code, text) or (None, None) if unreachable. Never raises.
    """
    try:
        full_url = urljoin(base_url, path)
        r = session.get(full_url, timeout=timeout)
        return r.status_code, r.text
    except requests.RequestException:
        return None, None
