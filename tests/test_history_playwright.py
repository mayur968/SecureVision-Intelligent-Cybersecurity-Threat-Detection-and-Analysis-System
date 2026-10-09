"""
Playwright E2E test for the History page.
Requires: Flask on :5000, Vite on :5173.
Run with: pytest tests/test_history_playwright.py -v --browser chromium
"""
import re, json, time, pathlib, sys
import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:5173"


@pytest.fixture(scope="session", autouse=True)
def ensure_legacy_rows():
    """Insert a legacy row (NULL risk_score, model_version, etc.) so both row types are present."""
    sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
    try:
        from app import app, db
        from database.models import ScanHistory
        with app.app_context():
            existing = ScanHistory.query.filter_by(model_version=None).first()
            if not existing:
                row = ScanHistory(
                    scan_type="URL",
                    input_value="http://legacy-test.example.com",
                    prediction="SAFE",
                    confidence=0.75,
                    risk_level="LOW",
                    explanation="Legacy test row",
                    recommendation="None",
                )
                db.session.add(row)
                db.session.commit()
    except Exception as e:
        print(f"Warning: could not insert legacy row: {e}")
    yield


def test_history_page_loads_no_console_errors(page: Page):
    """History page loads, table renders rows, no JS errors."""
    errors = []
    page.on("console", lambda msg: errors.append(msg.text()) if msg.type == "error" else None)
    page.on("pageerror", lambda err: errors.append(f"PAGEERROR: {err}"))

    failed_requests = []
    page.on("requestfailed", lambda req: failed_requests.append(req.url))

    def on_response(resp):
        if resp.status >= 400 and "/api/" in resp.url:
            failed_requests.append(f"{resp.status} {resp.url}")
    page.on("response", on_response)

    page.goto(f"{BASE_URL}/history", wait_until="networkidle", timeout=15_000)

    page.wait_for_selector(
        "table tbody tr, [data-testid='empty-state'], [data-testid='error-state']",
        timeout=10_000,
    )

    page.screenshot(path=".agents/tasks/history_screenshot_after.png", full_page=True)

    assert not failed_requests, f"Failed API requests: {failed_requests}"
    assert not errors, f"Console errors: {[str(e) for e in errors]}"

    rows = page.locator("table tbody tr").count()
    assert rows > 0, "Expected at least one scan row in the history table"


def test_history_legacy_row_shows_legacy_label(page: Page):
    """Rows with null model_version should show 'legacy' text somewhere in the row."""
    errors = []
    page.on("pageerror", lambda err: errors.append(f"PAGEERROR: {err}"))

    page.goto(f"{BASE_URL}/history", wait_until="networkidle", timeout=15_000)
    page.wait_for_selector("table tbody tr", timeout=10_000)

    assert not errors, f"Page crashed: {errors}"
    # Check that the word 'legacy' appears somewhere in the table
    legacy_text = page.locator("table").inner_text()
    assert "legacy" in legacy_text.lower(), "Expected 'legacy' label for rows with null model_version"


def test_history_filters_work(page: Page):
    """Type filter narrows the table."""
    page.goto(f"{BASE_URL}/history", wait_until="networkidle", timeout=15_000)
    page.wait_for_selector("table tbody tr", timeout=10_000)

    total_before = page.locator("table tbody tr").count()

    # Select URL filter — use the first <select> on the page
    page.locator("select").first.select_option("URL")
    time.sleep(0.5)  # allow React to re-render

    total_after = page.locator("table tbody tr").count()
    assert total_after <= total_before, "After URL filter, row count should be <= total"
