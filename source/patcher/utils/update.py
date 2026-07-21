import json
import sys
import urllib.request
import urllib.error
import webbrowser

from patcher.constants import VERSION, COLOR_CYAN, COLOR_GREEN, COLOR_YELLOW, COLOR_RED, COLOR_BOLD
from patcher.utils.console import color, info, ok, warn, err, hint


GITHUB_REPO = "AvenCores/open-antigravity-patcher"
RELEASES_URL = f"https://github.com/{GITHUB_REPO}/releases"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def _parse_version(v):
    """Parse a version string like '1.2.6' into a tuple of ints."""
    v = v.strip().lstrip("vV")
    parts = []
    for p in v.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            break
    return tuple(parts)


def _fetch_latest_release():
    """Fetch latest release info from GitHub API. Returns (tag, html_url) or (None, None)."""
    req = urllib.request.Request(API_URL, headers={
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": f"OpenAGPatcher/{VERSION}",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            tag = data.get("tag_name", "")
            html_url = data.get("html_url", "")
            return tag, html_url
    except (urllib.error.URLError, OSError, json.JSONDecodeError, KeyError):
        return None, None


def check_for_updates(silent=True):
    """Check for updates. Returns True if an update is available.

    If silent=True, only prints a message if an update is found.
    If silent=False, always prints the result.
    """
    tag, url = _fetch_latest_release()

    if tag is None:
        if not silent:
            warn("Could not check for updates (network error).")
        return False

    current = _parse_version(VERSION)
    latest = _parse_version(tag)

    if latest > current:
        info(f"New version available: {color(tag, COLOR_GREEN, COLOR_BOLD)} (current: {color(VERSION, COLOR_YELLOW)})")
        hint(f"Download: {color(url, COLOR_CYAN)}")
        print()
        return True

    if not silent:
        ok(f"Already up to date (v{VERSION})")
    return False


def open_releases_page():
    """Open the GitHub releases page in the default browser."""
    webbrowser.open(RELEASES_URL)
    ok(f"Opening: {color(RELEASES_URL, COLOR_CYAN)}")
