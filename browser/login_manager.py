import getpass
import time
from pathlib import Path
from typing import Optional

from playwright.sync_api import Page, BrowserContext

from browser.browser_utils import load_session, save_session, take_screenshot


SESSION_FILE = "jdy_session.json"


def ensure_logged_in(
    page: Page,
    context: BrowserContext,
    login_func,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> bool:
    if load_session(context, SESSION_FILE):
        page.goto("https://www.jdy.com/", wait_until="networkidle")
        time.sleep(2)
        if "login" not in page.url.lower():
            return True

    if not username:
        username = input("请输入金蝶账号: ").strip()
    if not password:
        password = getpass.getpass("请输入金蝶密码: ")

    success = login_func(username, password)
    if success:
        save_session(context, SESSION_FILE)
    return success


def clear_session():
    session_path = Path(SESSION_FILE)
    if session_path.exists():
        session_path.unlink()
