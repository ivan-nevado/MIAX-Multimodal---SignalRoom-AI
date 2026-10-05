"""End-to-end UI run against a live local stack + README screenshots.

Prerequisites: backend on :8000 (BACKEND_MODE=local) and frontend dev server on :5173.
Uses the system Google Chrome through Playwright (no browser download):
    pip install playwright
    python scripts/e2e_screenshots.py [--base http://localhost:5173]

It signs up a fresh user, runs a real "Why?" investigation, a multimodal research
investigation (PDF + audio), a follow-up, a briefing with audio + email preview, and
stores screenshots in docs/screenshots/. Any browser console error fails the run.
"""

from __future__ import annotations

import argparse
import sys
import time
import uuid
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs" / "screenshots"
DEMO = ROOT / "demo_data"


def shot(page: Page, name: str, full: bool = False) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=full)
    print(f"  📸 {name}.png")


def wait_for_text(page: Page, text: str, timeout_s: int) -> None:
    page.get_by_text(text, exact=False).first.wait_for(timeout=timeout_s * 1000)


def check_links(page: Page, base: str, pages: list[str], problems: list[str]) -> int:
    """Visit every internal link found on `pages`; fail on 404 pages or missing #anchors."""
    seen: set[str] = set()
    for src in pages:
        page.goto(base + src)
        page.wait_for_timeout(800)
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.getAttribute('href'))")
        for href in hrefs:
            if not href or href.startswith(("http", "mailto:")):
                continue
            target = href if href.startswith("/") else src.split("#")[0] + href
            if target in seen:
                continue
            seen.add(target)
            page.goto(base + target)
            page.wait_for_timeout(700)
            if page.get_by_text("No signal here.").count():
                problems.append(f"{src} -> {href}: 404 page")
            if "#" in target:
                anchor = target.split("#", 1)[1]
                if anchor and page.locator(f"[id='{anchor}']").count() == 0:
                    problems.append(f"{src} -> {href}: missing #{anchor}")
    return len(seen)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:5173")
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()
    errors: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=not args.headed)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        page = ctx.new_page()
        page.on("console", lambda m: m.type == "error" and errors.append(m.text))
        page.on("pageerror", lambda e: errors.append(str(e)))

        print("1. Landing page")
        page.goto(args.base + "/")
        expect(page.get_by_role("heading", name="Know what moved the market. Know why.")).to_be_visible()
        page.wait_for_timeout(1800)
        shot(page, "01-landing")
        shot(page, "01-landing-full", full=True)

        print("1b. Public link check")
        link_problems: list[str] = []
        n = check_links(page, args.base, ["/", "/about", "/privacy", "/terms", "/methodology", "/login", "/signup"], link_problems)
        print(f"   checked {n} public links")
        page.goto(args.base + "/methodology#evidence-scoring")
        page.get_by_role("heading", name="Methodology").wait_for()
        page.wait_for_timeout(1200)
        shot(page, "20-methodology")

        print("2. Sign up")
        email = f"e2e-{uuid.uuid4().hex[:8]}@signalroom.test"
        page.goto(args.base + "/signup")
        page.get_by_label("Email").fill(email)
        page.get_by_label("Password").fill("Sup3rSecret!")
        shot(page, "02-signup")
        page.get_by_role("button", name="Create account").click()
        page.wait_for_url("**/app/dashboard")

        print("3. Dashboard")
        page.get_by_text("$", exact=False).first.wait_for(timeout=60000)
        page.get_by_role("button", name="Why did NVIDIA move?").first.wait_for(timeout=60000)
        page.wait_for_timeout(2500)
        shot(page, "03-dashboard")

        print("4. Why? → live agent progress")
        page.get_by_role("button", name="Why did NVIDIA move?").first.click()
        page.wait_for_url("**/app/investigation/**")
        wait_for_text(page, "assembling your research team", 30)
        page.wait_for_timeout(9000)
        shot(page, "04-investigation-progress")
        started = time.time()
        page.get_by_role("tab", name="Summary").wait_for(timeout=300000)
        print(f"   investigation completed in {time.time() - started:.0f}s")
        page.wait_for_timeout(2000)
        shot(page, "05-investigation-summary")

        print("5. Evidence graph, market, risk, sources")
        page.get_by_role("tab", name="Drivers & evidence").click()
        page.wait_for_timeout(2500)
        shot(page, "06-evidence-graph")
        page.get_by_role("tab", name="Market").click()
        page.wait_for_timeout(2500)
        shot(page, "07-market")
        page.get_by_role("tab", name="Risk").click()
        page.wait_for_timeout(1500)
        shot(page, "08-risk")
        page.get_by_role("tab", name="Financials").click()
        page.wait_for_timeout(1000)
        shot(page, "09-financials")

        print("6. Follow-up")
        page.get_by_role("tab", name="Summary").click()
        page.get_by_label("Follow-up question").fill("What would invalidate this explanation?")
        page.get_by_role("button", name="Send follow-up").click()
        page.get_by_text("Evidence:", exact=False).last.wait_for(timeout=120000)
        page.get_by_label("Follow-up question").scroll_into_view_if_needed()
        page.wait_for_timeout(1000)
        shot(page, "10-followup")

        print("7. Multimodal research: PDF + earnings-call audio + results webinar video")
        page.goto(args.base + "/app/research")
        page.get_by_label("What do you want to understand?").fill("Summarize this earnings call and the results release. Does it change the thesis?")
        page.locator('input[type="file"]').set_input_files([str(DEMO / "northwind_q3_fy2026_results.pdf"), str(DEMO / "earnings_call.wav"), str(DEMO / "northwind_webinar.mp4")])
        page.get_by_label("Uploaded").nth(2).wait_for(timeout=60000)
        shot(page, "11-research-composer")
        page.get_by_role("button", name="Investigate").click()
        page.wait_for_url("**/app/investigation/**")
        page.get_by_role("tab", name="Documents & media").wait_for(timeout=300000)
        page.get_by_role("tab", name="Documents & media").click()
        page.wait_for_timeout(1500)
        shot(page, "12-multimodal-findings")
        page.get_by_role("button", name="Show full transcript").first.click()
        page.wait_for_timeout(2000)
        shot(page, "13-transcript")

        print("7b. Multimodal semantic search")
        page.goto(args.base + "/app/search")
        page.get_by_label("Search your research").fill("what did the CFO say about gross margin")
        page.get_by_role("list", name="Search results").wait_for(timeout=60000)
        page.wait_for_timeout(800)
        shot(page, "13b-semantic-search")
        page.locator('input[aria-label="Query image"]').set_input_files(str(DEMO / "nvda_chart.png"))
        page.get_by_text("Results similar to").wait_for(timeout=60000)
        page.wait_for_timeout(2500)
        shot(page, "13c-search-by-image")

        print("8. Asset page")
        page.goto(args.base + "/app/asset/NVDA")
        page.get_by_role("figure", name="NVDA price chart").wait_for(timeout=60000)
        page.wait_for_timeout(3500)
        shot(page, "14-asset")

        print("9. Briefing with audio + email preview")
        page.goto(args.base + "/app/briefings")
        page.get_by_role("button", name="Generate briefing now").click()
        page.locator('a[href^="/app/briefing/brf_"]').first.wait_for(timeout=30000)
        page.locator('a[href^="/app/briefing/brf_"]').first.click()
        page.get_by_role("button", name="Email preview").wait_for(timeout=300000)
        page.get_by_role("button", name="Play briefing").wait_for(timeout=300000)
        page.wait_for_timeout(1500)
        shot(page, "15-briefing")
        page.get_by_role("button", name="Email preview").click()
        page.wait_for_timeout(2500)
        shot(page, "16-email-preview")
        page.keyboard.press("Escape")

        print("9b. In-app link check")
        n = check_links(page, args.base, ["/app/dashboard", "/app/settings", "/app/briefings", "/app/research", "/app/search"], link_problems)
        print(f"   checked {n} in-app links")
        if link_problems:
            print("Broken links:", *link_problems, sep="\n  ")
            sys.exit(1)

        print("10. Settings")
        page.goto(args.base + "/app/settings")
        page.get_by_text("Daily briefing", exact=False).first.wait_for()
        page.wait_for_timeout(1500)
        shot(page, "17-settings")

        print("11. Mobile")
        mobile = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True, storage_state=ctx.storage_state())
        m = mobile.new_page()
        m.on("pageerror", lambda e: errors.append(str(e)))
        m.goto(args.base + "/app/dashboard")
        m.get_by_role("navigation", name="Mobile").wait_for()
        m.wait_for_timeout(4000)
        shot(m, "18-mobile-dashboard")
        m.goto(args.base + "/")
        m.wait_for_timeout(1500)
        shot(m, "19-mobile-landing")
        browser.close()

    relevant = [e for e in errors if "favicon" not in e.lower()]
    if relevant:
        print("Browser errors:\n  " + "\n  ".join(relevant[:20]))
        sys.exit(1)
    print("E2E run passed without browser errors.")


if __name__ == "__main__":
    main()
