from __future__ import annotations

import re

import pytest

playwright_sync_api = pytest.importorskip("playwright.sync_api")
expect = playwright_sync_api.expect
sync_playwright = playwright_sync_api.sync_playwright


def test_ui_navigation_and_delete_flow(live_server: str) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()

        page.goto(f"{live_server}/", wait_until="domcontentloaded")

        cards = page.locator("#subdir-list .subdir-card")
        expect(cards).to_have_count(2)

        page.locator("#subdir-list .subdir-card", has_text="dir1").click()
        expect(page).to_have_url(re.compile(r".*/viewer\?directory_id=.*"))

        expect(page.locator("#image-index")).to_have_text("1 / 2")
        expect(page.locator("#image-name")).to_have_text("Aurelion.png")

        page.keyboard.press("ArrowRight")
        expect(page.locator("#image-index")).to_have_text("2 / 2")
        expect(page.locator("#image-name")).to_have_text("cat1.png")

        page.keyboard.press("ArrowLeft")
        expect(page.locator("#image-index")).to_have_text("1 / 2")
        expect(page.locator("#image-name")).to_have_text("Aurelion.png")

        page.keyboard.press("Escape")
        expect(page).to_have_url(re.compile(r".*/$"))
        expect(page.locator("#subdir-list .subdir-card")).to_have_count(2)

        page.locator("#subdir-list .subdir-card", has_text="dir1").click()
        expect(page).to_have_url(re.compile(r".*/viewer\?directory_id=.*"))
        expect(page.locator("#image-index")).to_have_text("1 / 2")
        expect(page.locator("#image-name")).to_have_text("Aurelion.png")

        page.keyboard.press("Delete")
        expect(page.locator("#image-index")).to_have_text("1 / 1")
        expect(page.locator("#image-name")).to_have_text("cat1.png")

        page.keyboard.press("Escape")
        expect(page).to_have_url(re.compile(r".*/$"))

        page.locator("#subdir-list .subdir-card", has_text="dir2").click()
        expect(page).to_have_url(re.compile(r".*/viewer\?directory_id=.*"))
        expect(page.locator("#image-index")).to_have_text("1 / 1")
        expect(page.locator("#image-name")).to_have_text("dog1.png")

        page.locator("#delete-current-image").click()
        expect(page.locator("#image-index")).to_have_text("0 / 0")
        expect(page.locator("#empty-message")).to_be_visible()

        browser.close()
