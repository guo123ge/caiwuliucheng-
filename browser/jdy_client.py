import time
from typing import Optional

from playwright.sync_api import Page

from browser.browser_utils import wait_and_click, wait_and_fill, take_screenshot


class JDYClient:
    def __init__(self, page: Page):
        self.page = page

    def login(self, username: str, password: str) -> bool:
        try:
            self.page.goto("https://www.jdy.com/login/", wait_until="networkidle")
            time.sleep(2)

            wait_and_fill(self.page, 'input[placeholder*="手机号"], input[name="username"]',
                          username, timeout=5000)
            wait_and_fill(self.page, 'input[type="password"], input[placeholder*="密码"]',
                          password, timeout=5000)

            wait_and_click(self.page, 'button:has-text("登录"), button[type="submit"]',
                           timeout=5000)

            self.page.wait_for_load_state("networkidle")
            time.sleep(3)

            if "login" not in self.page.url.lower():
                take_screenshot(self.page, "login_success")
                return True
            else:
                take_screenshot(self.page, "login_failed")
                return False

        except Exception as e:
            take_screenshot(self.page, "login_error")
            raise RuntimeError(f"登录失败: {e}")

    def navigate_to_voucher_new(self):
        self.page.goto("https://www.jdy.com/", wait_until="networkidle")
        time.sleep(2)

        try:
            wait_and_click(self.page, 'text=凭证', timeout=5000)
            time.sleep(1)
            wait_and_click(self.page, 'text=新增凭证', timeout=5000)
            time.sleep(2)
        except Exception:
            try:
                self.page.goto("https://www.jdy.com/accounting/voucher/new",
                               wait_until="networkidle")
                time.sleep(3)
            except Exception as e:
                raise RuntimeError(f"导航到凭证新增页面失败: {e}")

    def fill_voucher_entry(
        self,
        row_index: int,
        summary: str,
        subject: str,
        debit_amount: float = 0,
        credit_amount: float = 0,
    ):
        try:
            if row_index > 0:
                add_btn = self.page.locator('button:has-text("添加"), button:has-text("新增行")')
                if add_btn.count() > 0:
                    add_btn.first.click()
                    time.sleep(0.5)

            summary_inputs = self.page.locator('input[placeholder*="摘要"], textarea[placeholder*="摘要"]')
            if summary_inputs.count() > row_index:
                summary_inputs.nth(row_index).fill(summary)

            subject_inputs = self.page.locator('input[placeholder*="科目"]')
            if subject_inputs.count() > row_index:
                subject_inputs.nth(row_index).fill(subject)
                time.sleep(0.5)

            if debit_amount > 0:
                debit_inputs = self.page.locator('input[placeholder*="借方"]')
                if debit_inputs.count() > row_index:
                    debit_inputs.nth(row_index).fill(str(debit_amount))

            if credit_amount > 0:
                credit_inputs = self.page.locator('input[placeholder*="贷方"]')
                if credit_inputs.count() > row_index:
                    credit_inputs.nth(row_index).fill(str(credit_amount))

        except Exception as e:
            take_screenshot(self.page, f"fill_voucher_error_row{row_index}")
            raise RuntimeError(f"填写凭证第{row_index}行失败: {e}")

    def save_voucher(self):
        try:
            wait_and_click(self.page, 'button:has-text("保存"), button:has-text("提交")',
                           timeout=5000)
            time.sleep(2)
            take_screenshot(self.page, "voucher_saved")
        except Exception as e:
            take_screenshot(self.page, "save_voucher_error")
            raise RuntimeError(f"保存凭证失败: {e}")
