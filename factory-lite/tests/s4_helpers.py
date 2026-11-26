"""Shared black-box helpers for the Stage 4 (factory-lite/spec/stage-4.md)
acceptance test contract.

Scope:
- Desktop and Mobile Playwright context configurations
- Slow-network throttling route interception
- Submission deliverable analyzers (word counts, duration budget, rubric checks)
"""
import inspect
import json
import os
import re
import sys
import time
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent.parent

if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from s2_helpers import AppProcess, app_base_url


MOBILE_VIEWPORT = {"width": 375, "height": 667}
DESKTOP_VIEWPORT = {"width": 1280, "height": 720}
MOBILE_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)

# Stage 4 Submission Document Candidates
README_PATH = REPO_ROOT / "README.md"
DOCS_DIR = REPO_ROOT / "docs"
FACTORY_DOCS_DIR = REPO_ROOT / "factory-lite" / "docs"

DEMO_SCRIPT_PATHS = [
    DOCS_DIR / "demo-script.md",
    FACTORY_DOCS_DIR / "demo-script.md",
    REPO_ROOT / "DEMO_SCRIPT.md",
    README_PATH,
]

WRITEUP_PATHS = [
    DOCS_DIR / "writeup.md",
    FACTORY_DOCS_DIR / "writeup.md",
    REPO_ROOT / "WRITEUP.md",
    README_PATH,
]

REAL_MOCK_MATRIX_PATHS = [
    DOCS_DIR / "real-mock-matrix.md",
    FACTORY_DOCS_DIR / "real-mock-matrix.md",
    REPO_ROOT / "REAL_MOCK_MATRIX.md",
    README_PATH,
]

RUBRIC_SELFCHECK_PATHS = [
    DOCS_DIR / "judging-rubric.md",
    FACTORY_DOCS_DIR / "judging-rubric.md",
    REPO_ROOT / "JUDGING_RUBRIC.md",
    README_PATH,
]


def create_desktop_context(browser):
    """Creates a desktop Playwright browser context."""
    return browser.new_context(
        viewport=DESKTOP_VIEWPORT,
        is_mobile=False,
        has_touch=False,
    )


def create_mobile_context(browser):
    """Creates a mobile Playwright browser context with touch emulation."""
    return browser.new_context(
        viewport=MOBILE_VIEWPORT,
        user_agent=MOBILE_USER_AGENT,
        is_mobile=True,
        has_touch=True,
    )


def attach_slow_network(context, delay_ms=500):
    """Introduces artificial latency on /api/rehearsal/ routes."""
    def handle_route(route):
        time.sleep(delay_ms / 1000.0)
        route.continue_()

    context.route("**/api/rehearsal/**", handle_route)


def find_first_existing_file(paths, required_heading=None):
    """Returns (path, text) of the first existing file matching criteria, or (None, None)."""
    for p in paths:
        if p.is_file():
            content = p.read_text(encoding="utf-8")
            if required_heading is None:
                return p, content
            if required_heading.lower() in content.lower():
                return p, content
    return None, None


def count_words_in_markdown(text):
    """Counts non-code words in markdown text."""
    # Remove code blocks
    cleaned = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    # Remove inline code
    cleaned = re.sub(r"`.*?`", "", cleaned)
    # Remove markdown link syntax [text](url) -> text
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    # Remove headers and punctuation symbols
    cleaned = re.sub(r"[#*_\->|:]", " ", cleaned)
    words = [w for w in cleaned.split() if w.strip()]
    return len(words)
