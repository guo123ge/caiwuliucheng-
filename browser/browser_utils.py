import json
import time
from pathlib import Path
from typing import Optional

from playwright.sync_api import Page, Browser, BrowserContext, sync_playwright


def launch_browser(headless: bool = False) -> tuple[Browser, BrowserContext, Page]:
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=headless)
    context = browser.new_context(
        viewport={"width": 1280, "height": 800},
        locale="zh-CN",
    )
    page = context.new_page()
    return browser, context, page


def wait_and_click(page: Page, selector: str, timeout: int = 10000):
    page.wait_for_selector(selector, timeout=timeout)
    page.click(selector)


def wait_and_fill(page: Page, selector: str, value: str, timeout: int = 10000):
    page.wait_for_selector(selector, timeout=timeout)
    page.fill(selector, value)


def take_screenshot(page: Page, name: str, output_dir: str = "screenshots"):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    path = str(Path(output_dir) / f"{name}_{timestamp}.png")
    page.screenshot(path=path, full_page=True)
    return path


def save_session(context: BrowserContext, path: str = "session.json"):
    cookies = context.cookies()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)


def load_session(context: BrowserContext, path: str = "session.json") -> bool:
    session_path = Path(path)
    if not session_path.exists():
        return False
    with open(session_path, "r", encoding="utf-8") as f:
        cookies = json.load(f)
    context.add_cookies(cookies)
    return True
