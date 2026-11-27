"""Stage 4C (responsive UI and packaging) black-box test helpers.

Not a test module itself (does not match ``test_*.py``). Browser tests drive
the real application through Playwright at the localhost URL documented in
``app/RUN.md``; packaging tests read repository artifacts. Nothing here talks
to a live vendor, reads credentials, or captures media.

The contract is documented in
``factory-lite/docs/stage-4c-acceptance-contract.md``.
"""
import json
import re
import urllib.error
import urllib.request
from pathlib import Path

from s2_helpers import AppProcess, app_base_url
from test_req2_health_version import assert_local_health_url

REPO_ROOT = Path(__file__).resolve().parents[2]

VIEWPORTS = {
    "desktop": {"width": 1280, "height": 800},
    "mobile": {"width": 375, "height": 667},
}

REQUIRED_TESTIDS = (
    "mode-label",
    "napster-status",
    "napster-avatar",
    "start-demo",
    "take-my-seat",
    "mic-denied-fallback",
    "practice-input",
    "send-utterance",
    "feedback-score",
    "retry-button",
    "thinking-indicator",
    "recording-indicator",
    "end-and-delete",
    "cleanup-status",
)


def start_app():
    return AppProcess().start()


def new_context(browser, viewport_name, permissions=()):
    viewport = VIEWPORTS[viewport_name]
    return browser.new_context(viewport=dict(viewport), permissions=list(permissions))


def goto_home(page):
    page.goto(app_base_url() + "/", wait_until="domcontentloaded")
    assert_visible(page, '[data-testid="start-demo"]', "landing page did not render")


def locator(page, selector):
    return page.locator(selector)


def is_visible(page, selector):
    try:
        return page.locator(selector).is_visible()
    except Exception:
        return False


def assert_visible(page, selector, message, timeout=5000):
    try:
        page.locator(selector).wait_for(state="visible", timeout=timeout)
    except Exception:
        raise AssertionError(f"{message} (selector {selector!r} not visible within {timeout} ms)")


def assert_hidden(page, selector, message, timeout=5000):
    try:
        page.locator(selector).wait_for(state="hidden", timeout=timeout)
    except Exception:
        raise AssertionError(f"{message} (selector {selector!r} still visible after {timeout} ms)")


def click(page, selector, message=None):
    assert_visible(page, selector, message or f"control {selector!r} is not available")
    page.locator(selector).click()


def start_demo(page):
    click(page, '[data-testid="start-demo"]', "start demo is not available")
    assert_visible(page, '[data-testid="take-my-seat"]', "demonstration did not start")


def take_my_seat(page):
    click(page, '[data-testid="take-my-seat"]', "handoff is not available")
    assert_visible(page, '[data-testid="practice-input"]', "practice did not start")


def to_practice(page):
    with page.expect_response(
        lambda r: r.request.method == "POST" and r.url.rstrip("/").endswith("/api/rehearsal/sessions"),
        timeout=15000,
    ) as info:
        start_demo(page)
    try:
        sid = info.value.json().get("session_id")
    except Exception:
        sid = None
    take_my_seat(page)
    return sid


def send_text(page, text):
    assert_visible(page, '[data-testid="practice-input"]', "practice input is not available")
    page.locator('[data-testid="practice-input"]').fill(text)
    click(page, '[data-testid="send-utterance"]', "send control is not available")


def finish_attempt(page):
    page.locator('[data-testid="practice-input"]').fill("")
    click(page, '[data-testid="send-utterance"]', "send control is not available")
    assert_visible(page, '[data-testid="feedback-score"]', "feedback was not shown")


def retry(page):
    click(page, '[data-testid="retry-button"]', "retry is not available")
    assert_visible(page, '[data-testid="practice-input"]', "retry did not return to practice")


def session_id(page):
    """Read the page's session id from its script scope."""
    try:
        return page.evaluate("() => (typeof sid !== 'undefined' ? sid : null)")
    except Exception:
        return None


def api_get_json(path):
    url = app_base_url() + path
    assert_local_health_url(url)
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            body = None
        return exc.code, body


def viewport_meta_content(page):
    return page.evaluate(
        "() => { const m = document.querySelector('meta[name=\"viewport\"]');"
        " return m ? m.getAttribute('content') : null; }"
    )


def scroll_widths(page):
    return page.evaluate(
        "() => ({ html: document.documentElement.scrollWidth,"
        " body: document.body.scrollWidth, inner: window.innerWidth,"
        " innerHeight: window.innerHeight })"
    )


def bounding_box(page, selector):
    return page.locator(selector).bounding_box()


def focus_indicator(page, selector):
    """Return the computed focus style after focusing ``selector``."""
    page.locator(selector).focus()
    return page.evaluate(
        "(sel) => { const el = document.querySelector(sel);"
        " const s = getComputedStyle(el);"
        " return { outlineStyle: s.outlineStyle, outlineWidth: s.outlineWidth,"
        " boxShadow: s.boxShadow, focusVisible: el.matches(':focus-visible') }; }",
        selector,
    )


def press_enter_on(page, selector):
    page.locator(selector).focus()
    page.keyboard.press("Enter")


# ---------------------------------------------------------------------------
# Packaging helpers
# ---------------------------------------------------------------------------

def read_repo_text(relative_path):
    path = REPO_ROOT / relative_path
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def word_count(text):
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'_-]*", text))


def markdown_table_rows(text):
    rows = [line for line in text.splitlines() if line.strip().startswith("|")]
    # Drop separator rows such as |---|---|
    return [line for line in rows if not re.fullmatch(r"\|[\s:|-]+\|", line.strip())]
