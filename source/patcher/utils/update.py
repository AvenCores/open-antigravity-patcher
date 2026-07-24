import json
import sys
import urllib.request
import urllib.error
import webbrowser

from patcher.constants import VERSION, COLOR_CYAN, COLOR_GREEN, COLOR_YELLOW, COLOR_RED, COLOR_BOLD
from patcher.utils.console import color, info, ok, warn, err, hint, _frame_border, _frame_row


GITHUB_REPO = "AvenCores/open-antigravity-patcher"
RELEASES_URL = f"https://github.com/{GITHUB_REPO}/releases"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

LAST_UPDATE_RESULT = None


def get_last_update_result():
    return LAST_UPDATE_RESULT


def set_last_update_result(result):
    global LAST_UPDATE_RESULT
    LAST_UPDATE_RESULT = result


def print_network_error_warning():
    """Print a noticeable warning and VPN recommendation when check_for_updates fails interactively."""
    warn("Could not check for updates (network error).")
    hint("Recommendation: Turn on VPN to connect to GitHub and check for updates.")


def print_network_error_banner():
    """Print a framed warning banner in the main menu when update check failed due to network error."""
    print(f"  {_frame_border('╔', '═', '╗', COLOR_YELLOW)}")
    print(f"  {_frame_row(color('WARNING: Update check failed (network error)', COLOR_YELLOW, COLOR_BOLD), accent=COLOR_YELLOW)}")
    print(f"  {_frame_row(color('Turn on VPN to check for updates on GitHub', COLOR_CYAN, COLOR_BOLD), accent=COLOR_YELLOW)}")
    print(f"  {_frame_border('╚', '═', '╝', COLOR_YELLOW)}")
    print()


def print_update_status_notice():
    """Prints update notice, up-to-date status, or network error warning banner in the main menu."""
    if LAST_UPDATE_RESULT == "network_error":
        print_network_error_banner()
    elif isinstance(LAST_UPDATE_RESULT, tuple) and LAST_UPDATE_RESULT[0] == "update_available":
        _, tag, url = LAST_UPDATE_RESULT
        info(f"New version available: {color(tag, COLOR_GREEN, COLOR_BOLD)} (current: {color(VERSION, COLOR_YELLOW)})")
        hint(f"Download: {color(url, COLOR_CYAN)}")
        print()
    elif LAST_UPDATE_RESULT == "up_to_date":
        ok(f"Patcher is up to date (v{VERSION})")
        print()


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


def _fetch_latest_release(timeout=5):
    """Fetch latest release info from GitHub API. Returns (tag, html_url) or (None, None)."""
    req = urllib.request.Request(API_URL, headers={
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": f"OpenAGPatcher/{VERSION}",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            tag = data.get("tag_name", "")
            html_url = data.get("html_url", "")
            return tag, html_url
    except Exception:
        return None, None


def check_for_updates(silent=True, timeout=5):
    """Check for updates. Returns True if an update is available.

    If silent=True, only prints a message if an update is found.
    If silent=False, always prints the result.
    """
    global LAST_UPDATE_RESULT
    tag, url = _fetch_latest_release(timeout=timeout)

    if tag is None:
        LAST_UPDATE_RESULT = "network_error"
        if not silent:
            print_network_error_warning()
        return False

    current = _parse_version(VERSION)
    latest = _parse_version(tag)

    if latest > current:
        LAST_UPDATE_RESULT = ("update_available", tag, url)
        if not silent:
            info(f"New version available: {color(tag, COLOR_GREEN, COLOR_BOLD)} (current: {color(VERSION, COLOR_YELLOW)})")
            hint(f"Download: {color(url, COLOR_CYAN)}")
        return True

    LAST_UPDATE_RESULT = "up_to_date"
    if not silent:
        ok(f"Already up to date (v{VERSION})")
    return False


def open_releases_page():
    """Open the GitHub releases page in the default browser."""
    webbrowser.open(RELEASES_URL)
    ok(f"Opening: {color(RELEASES_URL, COLOR_CYAN)}")
