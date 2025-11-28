import os
import sys

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
OUT = os.path.join(os.path.dirname(__file__), "..", "results_screenshots")
os.makedirs(OUT, exist_ok=True)

pages = [
    ("dashboard", BASE + "/"),
    ("resultaten", BASE + "/resultaten"),
]

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(
        viewport={"width": 1366, "height": 768},
        user_agent="Mozilla/5.0 (X11; Linux x86_64)",
    )
    page = context.new_page()
    for name, url in pages:
        try:
            page.goto(url, wait_until="networkidle", timeout=15000)
            page.screenshot(
                path=os.path.join(OUT, f"{name}_desktop.png"), full_page=True
            )
            print("Saved", name, "desktop")
        except Exception as e:
            print("Failed desktop", name, e)
    # mobile emulation
    iphone = p.devices["iPhone 12"]
    context2 = browser.new_context(**iphone)
    page2 = context2.new_page()
    for name, url in pages:
        try:
            page2.goto(url, wait_until="networkidle", timeout=15000)
            page2.screenshot(
                path=os.path.join(OUT, f"{name}_mobile.png"), full_page=True
            )
            print("Saved", name, "mobile")
        except Exception as e:
            print("Failed mobile", name, e)
    browser.close()
