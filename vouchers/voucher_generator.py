from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

from vouchers.subject_mapping import get_full_mapping


def generate_bank_vouchers(
    classified_df: pd.DataFrame,
    voucher_date: Optional[str] = None,
) -> pd.DataFrame:
    if voucher_date is None:
        voucher_date = datetime.now().strftime("%Y-%m-%d")

    df = classified_df.copy()
    if "分类" not in df.columns:
        return pd.DataFrame()

    df = df[~df["分类"].str.contains("待确认", na=False)]

    voucher_rows = []
    voucher_no = 1

    categories = df["分类"].dropna().unique()
    for cat in categories:
        mapping = get_full_mapping(cat, is_invoice=False)
        if not mapping:
            continue

        subset = df[df["分类"] == cat]
        total_income = pd.to_numeric(subset.get("收入金额", 0), errors="coerce").sum()
        total_expense = pd.to_numeric(subset.get("支出金额", 0), errors="coerce").sum()

        debit_amount = total_expense if total_expense > 0 else total_income
        credit_amount = total_income if total_income > 0 else total_expense

        if debit_amount == 0 and credit_amount == 0:
            continue

        if debit_amount > 0:
            voucher_rows.append({
                "凭证号": f"记-{voucher_no:04d}",
                "日期": voucher_date,
                "摘要": f"{cat}",
                "科目名称": mapping.get("debit", ""),
                "科目编码": mapping.get("debit_code", ""),
                "借方金额": round(debit_amount, 2),
                "贷方金额": 0,
            })

        if credit_amount > 0:
            voucher_rows.append({
                "凭证号": f"记-{voucher_no:04d}",
                "日期": voucher_date,
                "摘要": f"{cat}",
                "科目名称": mapping.get("credit", ""),
                "科目编码": mapping.get("credit_code", ""),
                "借方金额": 0,
                "贷方金额": round(credit_amount, 2),
            })

        voucher_no += 1

    return pd.DataFrame(voucher_rows)


def generate_invoice_vouchers(
    invoice_df: pd.DataFrame,
    voucher_date: Optional[str] = None,
) -> pd.DataFrame:
    if voucher_date is None:
        voucher_date = datetime.now().strftime("%Y-%m-%d")

    df = invoice_df.copy()
    if "发票分类" not in df.columns:
        return pd.DataFrame()

    df = df[~df["发票分类"].str.contains("待确认", na=False)]

    voucher_rows = []
    voucher_no = 1

    categories = df["发票分类"].dropna().unique()
    for cat in categories:
        mapping = get_full_mapping(cat, is_invoice=True)
        if not mapping:
            continue

        subset = df[df["发票分类"] == cat]
        total_amount = pd.to_numeric(subset.get("金额", 0), errors="coerce").sum()

        if total_amount <= 0:
            continue

        voucher_rows.append({
            "凭证号": f"记-{voucher_no:04d}",
            "日期": voucher_date,
            "摘要": f"发票-{cat}",
            "科目名称": mapping.get("debit", ""),
            "科目编码": mapping.get("debit_code", ""),
            "借方金额": round(total_amount, 2),
            "贷方金额": 0,
        })
        voucher_rows.append({
            "凭证号": f"记-{voucher_no:04d}",
            "日期": voucher_date,
            "摘要": f"发票-{cat}",
            "科目名称": mapping.get("credit", ""),
            "科目编码": mapping.get("credit_code", ""),
            "借方金额": 0,
            "贷方金额": round(total_amount, 2),
        })

        voucher_no += 1

    return pd.DataFrame(voucher_rows)


def generate_sales_vouchers(
    match_result: pd.DataFrame,
    voucher_date: Optional[str] = None,
) -> pd.DataFrame:
    if voucher_date is None:
        voucher_date = datetime.now().strftime("%Y-%m-%d")

    df = match_result.copy()
    if "状态" not in df.columns:
        return pd.DataFrame()

    need_voucher = df[df["状态"] == "INVOICE_NO_PAYMENT"]
    if need_voucher.empty:
        return pd.DataFrame()

    voucher_rows = []
    for voucher_no, (_, row) in enumerate(need_voucher.iterrows(), 1):
        amount = float(row.get("发票金额", 0) or 0)
        company = row.get("对方单位", "")

        voucher_rows.append({
            "凭证号": f"记-{voucher_no:04d}",
            "日期": voucher_date,
            "摘要": f"应付-{company}",
            "科目名称": "原材料/管理费用",
            "科目编码": "1403/6602",
            "借方金额": round(amount, 2),
            "贷方金额": 0,
        })
        voucher_rows.append({
            "凭证号": f"记-{voucher_no:04d}",
            "日期": voucher_date,
            "摘要": f"应付-{company}",
            "科目名称": "应付账款",
            "科目编码": "2202",
            "借方金额": 0,
            "贷方金额": round(amount, 2),
        })

    return pd.DataFrame(voucher_rows)
