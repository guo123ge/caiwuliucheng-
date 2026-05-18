from pathlib import Path
from typing import List, Optional

import pandas as pd

from data.excel_writer import create_workbook_with_sheets, save_dataframe


def save_classified_bank_statement(
    df: pd.DataFrame,
    summary_df: pd.DataFrame,
    output_path: str,
):
    sheets = [
        {
            "name": "分类明细",
            "dataframe": df,
            "title": "银行流水分类明细",
            "number_cols": _find_number_cols(df, ["收入金额", "支出金额", "净额", "置信度"]),
        },
        {
            "name": "分类汇总",
            "dataframe": summary_df,
            "title": "银行流水分类汇总",
            "number_cols": _find_number_cols(summary_df, ["收入合计", "支出合计", "净额"]),
        },
    ]

    pending = df[df["分类"].str.contains("待确认", na=False)] if "分类" in df.columns else pd.DataFrame()
    if not pending.empty:
        sheets.append({
            "name": "待确认",
            "dataframe": pending,
            "title": "待人工确认条目",
            "number_cols": _find_number_cols(pending, ["收入金额", "支出金额"]),
        })

    create_workbook_with_sheets(sheets, output_path)


def save_classified_invoices(
    df: pd.DataFrame,
    summary_df: pd.DataFrame,
    output_path: str,
):
    sheets = [
        {
            "name": "发票分类明细",
            "dataframe": df,
            "title": "发票分类明细",
            "number_cols": _find_number_cols(df, ["金额", "税额", "分类置信度"]),
        },
        {
            "name": "发票分类汇总",
            "dataframe": summary_df,
            "title": "发票分类汇总",
            "number_cols": _find_number_cols(summary_df, ["金额合计", "税额合计"]),
        },
    ]

    pending = df[df["发票分类"].str.contains("待确认", na=False)] if "发票分类" in df.columns else pd.DataFrame()
    if not pending.empty:
        sheets.append({
            "name": "待确认",
            "dataframe": pending,
            "title": "待人工确认发票",
            "number_cols": _find_number_cols(pending, ["金额"]),
        })

    create_workbook_with_sheets(sheets, output_path)


def save_match_result(
    match_df: pd.DataFrame,
    pending_items: dict,
    output_path: str,
):
    sheets = [
        {
            "name": "关联分析",
            "dataframe": match_df,
            "title": "账户-发票关联分析",
            "number_cols": _find_number_cols(match_df, ["银行流水收入", "银行流水支出", "银行流水净额", "发票金额"]),
        },
    ]

    for name, pending_df in pending_items.items():
        if not pending_df.empty:
            sheets.append({
                "name": name[:31],
                "dataframe": pending_df,
                "title": name,
                "number_cols": _find_number_cols(pending_df, ["银行流水收入", "银行流水支出", "银行流水净额", "发票金额"]),
            })

    create_workbook_with_sheets(sheets, output_path)


def save_vouchers(
    bank_vouchers: pd.DataFrame,
    invoice_vouchers: pd.DataFrame,
    sales_vouchers: pd.DataFrame,
    output_dir: str,
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not bank_vouchers.empty:
        save_dataframe(
            bank_vouchers,
            str(output_dir / "记账凭证_银行流水.xlsx"),
            title="记账凭证 - 银行流水",
        )

    if not invoice_vouchers.empty:
        save_dataframe(
            invoice_vouchers,
            str(output_dir / "记账凭证_发票无收款.xlsx"),
            title="记账凭证 - 发票无收款",
        )

    if not sales_vouchers.empty:
        save_dataframe(
            sales_vouchers,
            str(output_dir / "记账凭证_销售.xlsx"),
            title="记账凭证 - 销售",
        )


def save_tax_report(tax_df: pd.DataFrame, output_path: str):
    save_dataframe(tax_df, output_path, title="当月税务测算表")


def save_financial_statements(
    balance_sheet: pd.DataFrame,
    income_statement: pd.DataFrame,
    output_dir: str,
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    save_dataframe(balance_sheet, str(output_dir / "资产负债表.xlsx"), title="资产负债表")
    save_dataframe(income_statement, str(output_dir / "损益表.xlsx"), title="损益表")


def _find_number_cols(df: pd.DataFrame, candidates: List[str]) -> List[int]:
    result = []
    for i, col in enumerate(df.columns, 1):
        if col in candidates:
            result.append(i)
    return result
