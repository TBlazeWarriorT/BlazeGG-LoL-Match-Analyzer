"""
Generates docs/showcase.png: a screenshot of the hub after an ID search for a
real match, for the README. Run manually whenever the UI changes enough to
make the current screenshot stale:

    py scripts/generate_showcase.py
    py scripts/generate_showcase.py --match-id KR_8326219860 --out docs/showcase.png

Uses a fixed match ID (Faker's, by default) rather than a live summoner search
on purpose: a summoner search pulls whatever that player's most recent games
are, so the screenshot would look different (and need regenerating) every
time they play. A single match ID is permanent — the shot stays accurate
until the UI itself changes.

Needs a working Riot API key in .env (DEV_KEY or PROD_KEY) unless that match
is already cached in data_cache/. Needs Playwright's Chromium (one-time):
    py -m playwright install chromium
"""
import argparse
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def wait_for_server(url: str, timeout: float = 20.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.3)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--match-id", default="KR_8368666881", help="Match ID to search by (default: one of Faker's real games, already cached with him as the recorded owner)")
    ap.add_argument("--out", default=str(BASE_DIR / "docs" / "showcase.png"))
    ap.add_argument("--port", type=int, default=8321, help="Uses a separate port so it won't collide with a dev server on 8000")
    args = ap.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright isn't installed. Run: pip install playwright && py -m playwright install chromium")
        sys.exit(1)

    env = os.environ.copy()
    env["PORT"] = str(args.port)
    env["BLAZE_AUTO_RELOAD"] = "1"  # skip the watchdog/parent process, go straight to serving
    env["BLAZE_ENV"] = "production"  # skip the interactive "kill it?" prompt and auto-opening a browser tab

    print(f"Starting a throwaway server on port {args.port}...")
    server = subprocess.Popen([sys.executable, str(BASE_DIR / "app.py")], env=env, cwd=str(BASE_DIR))
    try:
        base_url = f"http://127.0.0.1:{args.port}"
        if not wait_for_server(base_url):
            print("Server never came up.")
            sys.exit(1)

        analyze_url = f"{base_url}/analyze?" + urllib.parse.urlencode({"match_id": args.match_id})

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 720})

            # Hit /analyze first so this browser's blaze_id_searches cookie remembers
            # this match ID, then load the hub — which will show it under the
            # "ID Searches" tab, same as a real visitor pasting a match ID would see.
            print(f"Searching match {args.match_id}...")
            page.goto(analyze_url, wait_until="networkidle", timeout=30000)
            page.goto(base_url, wait_until="networkidle", timeout=30000)
            try:
                page.wait_for_selector(".match-item", timeout=20000)
            except Exception:
                print("Warning: no .match-item found (bad/expired API key and not cached?) — screenshotting whatever loaded anyway.")

            # Hide the personal Riot-key setup card — it's this machine's own session
            # key/expiry, not part of what the showcase is meant to demonstrate.
            page.evaluate("""() => {
                document.querySelectorAll('h3').forEach(h => {
                    if (/api key/i.test(h.textContent)) {
                        const card = h.closest('.section-card');
                        if (card) card.style.display = 'none';
                    }
                });
            }""")
            page.screenshot(path=str(out_path), full_page=True)
            browser.close()

        print(f"Saved {out_path}")
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    main()
