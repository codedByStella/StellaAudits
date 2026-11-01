"""
app.py
StellaAudits local audit tool -- a single Flask app covering everything:
single-URL audits, batch audits, the leads dashboard, and PDF/email-draft
downloads. One entry point (run_windows.bat) starts this and everything is
reachable from the one browser tab it opens -- no separate scripts to run.

Usage: double-click run_windows.bat. A browser tab opens to
http://127.0.0.1:5000 automatically.

Everything here is designed to be run locally by one person (no multi-user
auth, no external network exposure -- binds to 127.0.0.1 only).
"""

import os
import threading
import time
import uuid
import webbrowser

from flask import Flask, render_template, request, jsonify, send_from_directory

from audit.runner import run_full_audit
from audit.fetcher import FetchError
from audit.report import save_report_pdf, make_base_filename
from audit.outreach import save_email_draft, build_email_draft
from audit import db
import config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

# Seconds to wait between sites in a batch run -- a deliberate throttle so a
# long list never behaves like a crawl against any single site.
BATCH_THROTTLE_SECONDS = 3

app = Flask(__name__)

# In-memory batch progress store. This is a single-user local tool with no
# persistence requirement for in-flight progress -- if the app restarts
# mid-batch, the DB still has every completed row up to that point.
_batch_jobs = {}
_batch_jobs_lock = threading.Lock()


def _run_and_persist(url: str, include_deeper: bool) -> dict:
    """
    Shared by both the single-audit and batch endpoints: run one audit,
    save its PDF + email draft, log it to the leads DB, return a result dict.
    Never raises -- failures are captured and logged as a DB row too.
    """
    try:
        result = run_full_audit(url, include_deeper_detection=include_deeper)
    except FetchError as e:
        db.insert_failure(url, str(e))
        return {"ok": False, "url": url, "error": str(e)}
    except Exception as e:
        app.logger.exception("Unexpected error running audit for %s", url)
        db.insert_failure(url, f"Unexpected error: {e}")
        return {"ok": False, "url": url,
                "error": "Something went wrong running this audit. Check the URL and try again."}

    # Look up the most recent prior audit of this same domain (if any) before
    # writing the new row, so the PDF/API response can show a before/after
    # comparison.
    domain = db.domain_of(result.url)
    prior = db.get_latest_prior(domain)
    comparison = None
    if prior:
        diff = db.diff_findings(prior.get("findings_snapshot", ""), result.findings)
        comparison = {
            "previous_score": prior["score"],
            "previous_grade": prior["grade"],
            "previous_date": prior["audited_at"][:10],
            "score_delta": result.score - prior["score"],
            "resolved": diff["resolved"],
            "new": diff["new"],
        }

    try:
        stem = make_base_filename(result.url)
        pdf_path = save_report_pdf(result, REPORTS_DIR, base_filename=stem, comparison=comparison)
        pdf_filename = os.path.basename(pdf_path)
        email_filename = save_email_draft(result, config.get, REPORTS_DIR, stem)
    except Exception as e:
        app.logger.exception("Unexpected error generating report files for %s", url)
        db.insert_failure(url, f"Report generation failed: {e}")
        return {"ok": False, "url": url,
                "error": "The audit ran but report file generation failed."}

    lead_id = db.insert_success(
        url=result.url, score=result.score, grade=result.grade,
        total_findings=len(result.findings),
        pdf_filename=pdf_filename, email_draft_filename=email_filename,
        findings=result.findings,
    )
    draft = build_email_draft(result, config.get)

    return {
        "comparison": comparison,
        "ok": True,
        "lead_id": lead_id,
        "url": result.url,
        "total_findings": len(result.findings),
        "counts": result.counts_by_severity(),
        "score": result.score,
        "grade": result.grade,
        "download_url": f"/reports/{pdf_filename}",
        "email_draft_url": f"/reports/{email_filename}",
        "email_warnings": draft["warnings"],
    }


@app.route("/")
def index():
    return render_template("index.html", has_pagespeed_key=bool(config.get("pagespeed_api_key")))


@app.route("/audit", methods=["POST"])
def audit():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    include_deeper = bool(data.get("deeper", True))

    if not url:
        return jsonify(ok=False, error="Please enter a URL."), 400

    result = _run_and_persist(url, include_deeper)
    status = 200
    return jsonify(**result), status


@app.route("/batch", methods=["POST"])
def start_batch():
    data = request.get_json(silent=True) or {}
    raw_urls = data.get("urls") or []
    include_deeper = bool(data.get("deeper", True))

    urls = [u.strip() for u in raw_urls if u and u.strip()]
    # de-dupe while preserving order
    seen = set()
    urls = [u for u in urls if not (u in seen or seen.add(u))]

    if not urls:
        return jsonify(ok=False, error="No URLs provided."), 400
    if len(urls) > 100:
        return jsonify(ok=False, error="Batch limited to 100 URLs at a time."), 400

    batch_id = uuid.uuid4().hex
    with _batch_jobs_lock:
        _batch_jobs[batch_id] = {
            "total": len(urls), "done": 0, "results": [], "finished": False,
        }

    def _worker():
        for i, url in enumerate(urls):
            result = _run_and_persist(url, include_deeper)
            with _batch_jobs_lock:
                _batch_jobs[batch_id]["results"].append(result)
                _batch_jobs[batch_id]["done"] = i + 1
            if i < len(urls) - 1:
                time.sleep(BATCH_THROTTLE_SECONDS)
        with _batch_jobs_lock:
            _batch_jobs[batch_id]["finished"] = True

    threading.Thread(target=_worker, daemon=True).start()
    return jsonify(ok=True, batch_id=batch_id, total=len(urls))


@app.route("/batch/status/<batch_id>")
def batch_status(batch_id):
    with _batch_jobs_lock:
        job = _batch_jobs.get(batch_id)
        if not job:
            return jsonify(ok=False, error="Unknown batch id."), 404
        return jsonify(ok=True, **job)


@app.route("/leads")
def leads():
    status_filter = request.args.get("status") or None
    records = db.list_audits(status=status_filter)
    counts = db.summary_counts()
    total_count = sum(counts.values())
    return render_template("leads.html", records=records, counts=counts, total_count=total_count,
                            statuses=db.VALID_STATUSES, active_filter=status_filter)


@app.route("/leads/<int:lead_id>/status", methods=["POST"])
def update_lead_status(lead_id):
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    notes = data.get("notes")
    try:
        db.update_status(lead_id, new_status, notes=notes)
    except ValueError as e:
        return jsonify(ok=False, error=str(e)), 400
    return jsonify(ok=True)


@app.route("/reports/<path:filename>")
def download_report(filename):
    return send_from_directory(REPORTS_DIR, filename, as_attachment=True)


def _open_browser():
    time.sleep(1.2)
    webbrowser.open("http://127.0.0.1:5000")


if __name__ == "__main__":
    os.makedirs(REPORTS_DIR, exist_ok=True)
    threading.Thread(target=_open_browser, daemon=True).start()
    app.run(host="127.0.0.1", port=5000, debug=False)
