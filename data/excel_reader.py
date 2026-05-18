import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


COLUMN_ALIASES = {
    "date": [
        "交易日期", "日期", "记账日期", "交易时间", "发生日期", "入账日期",
        "date", "trade_date", "transaction_date", "交易时间",
    ],
    "description": [
        "摘要", "备注", "交易摘要", "交易备注", "用途", "摘要/备注",
        "description", "summary", "memo", "remark", "note", "摘要",
    ],
    "income": [
        "收入金额", "收入", "贷方金额", "贷方", "收款金额", "存入金额",
        "income", "credit", "deposit", "revenue",
        "贷方金额（收入）", "贷方金额(收入)", "贷方发生额",
    ],
    "expense": [
        "支出金额", "支出", "借方金额", "借方", "付款金额", "支取金额",
        "expense", "debit", "payment", "withdrawal",
        "借方金额（支出）", "借方金额(支出)", "借方发生额",
    ],
    "balance": [
        "余额", "账户余额", "当前余额", "balance", "current_balance",
    ],
    "counterparty": [
        "对方账户", "对方单位", "对方户名", "交易对方", "对方名称",
        "counterparty", "opposite_account", "payee", "payer",
        "对方户名",
    ],
    "invoice_date": [
        "发票日期", "开票日期", "invoice_date", "date",
    ],
    "invoice_number": [
        "发票号码", "发票号", "发票代码", "invoice_number", "invoice_no",
    ],
    "invoice_type": [
        "发票类型", "票据类型", "invoice_type",
    ],
    "amount": [
        "金额", "发票金额", "价税合计", "amount", "total_amount",
    ],
    "company": [
        "对方单位", "销方名称", "购方名称", "单位名称", "公司名称",
        "company", "seller", "buyer", "company_name",
    ],
    "goods_or_service": [
        "货物名称", "服务名称", "货物或应税劳务名称", "商品名称",
        "goods", "service", "product_name",
    ],
    "tax_amount": [
        "税额", "税金", "增值税额", "tax", "tax_amount",
    ],
    "tax_rate": [
        "税率", "tax_rate",
    ],
}


def _normalize_column_name(name: str) -> str:
    return str(name).strip().lower().replace(" ", "").replace("_", "")


def _find_column(df: pd.DataFrame, target: str) -> Optional[str]:
    normalized_target = _normalize_column_name(target)
    for col in df.columns:
        if _normalize_column_name(col) == normalized_target:
            return col
    return None


def _smart_match_column(df: pd.DataFrame, field: str) -> Optional[str]:
    aliases = COLUMN_ALIASES.get(field, [])
    for col in df.columns:
        normalized = _normalize_column_name(col)
        for alias in aliases:
            if _normalize_column_name(alias) == normalized:
                return col
    for col in df.columns:
        normalized = _normalize_column_name(col)
        for alias in aliases:
            if _normalize_column_name(alias) in normalized or normalized in _normalize_column_name(alias):
                return col
    return None


def read_excel(file_path: str, sheet_name: int | str = 0) -> pd.DataFrame:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    if path.suffix.lower() in (".xlsx", ".xls", ".xlsm"):
        df = pd.read_excel(file_path, sheet_name=sheet_name, dtype=str)
    elif path.suffix.lower() == ".csv":
        df = pd.read_csv(file_path, dtype=str)
    else:
        raise ValueError(f"不支持的文件格式: {path.suffix}")

    df = df.dropna(how="all")
    df.columns = [str(c).strip() for c in df.columns]
    return df


def read_bank_statement(file_path: str) -> pd.DataFrame:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    if path.suffix.lower() in (".xlsx", ".xls", ".xlsm"):
        raw = pd.read_excel(file_path, header=None, dtype=str)
    elif path.suffix.lower() == ".csv":
        raw = pd.read_csv(file_path, header=None, dtype=str)
    else:
        raise ValueError(f"不支持的文件格式: {path.suffix}")

    raw = raw.dropna(how="all")

    header_keywords = ["日期", "摘要", "借方", "贷方", "余额", "对方", "交易时间"]
    header_row = None
    for i in range(min(10, len(raw))):
        row_values = [str(v).strip() for v in raw.iloc[i].tolist() if pd.notna(v)]
        row_text = " ".join(row_values)
        matches = sum(1 for kw in header_keywords if kw in row_text)
        if matches >= 2:
            header_row = i
            break

    if header_row is None:
        header_row = 0

    columns = [str(c).strip() if pd.notna(c) else f"Unnamed_{j}" for j, c in enumerate(raw.iloc[header_row])]

    data = raw.iloc[header_row + 1:].copy()
    data.columns = columns
    data = data.reset_index(drop=True)

    unnamed_date_cols = [c for c in data.columns if c.startswith("Unnamed_")]
    if unnamed_date_cols and "date" not in [c for c in data.columns if c != unnamed_date_cols[0]]:
        first_unnamed = unnamed_date_cols[0]
        sample_vals = data[first_unnamed].dropna().head(5).tolist()
        looks_like_date = all(
            any(ch.isdigit() or ch in "-/: " for ch in str(v))
            for v in sample_vals if pd.notna(v)
        )
        if looks_like_date:
            data = data.rename(columns={first_unnamed: "date"})

    mapping = {}
    for field in ["date", "description", "income", "expense", "balance", "counterparty"]:
        col = _smart_match_column(data, field)
        if col:
            mapping[col] = field

    if mapping:
        data = data.rename(columns=mapping)

    required = ["date", "description"]
    for field in required:
        if field not in data.columns:
            found = _smart_match_column(data, field)
            if found:
                data = data.rename(columns={found: field})
            else:
                raise ValueError(f"无法识别'{field}'列，文件: {file_path}")

    if "income" in data.columns:
        data["income"] = pd.to_numeric(data["income"], errors="coerce").fillna(0)
    else:
        data["income"] = 0

    if "expense" in data.columns:
        data["expense"] = pd.to_numeric(data["expense"], errors="coerce").fillna(0)
    else:
        data["expense"] = 0

    if "balance" in data.columns:
        data["balance"] = pd.to_numeric(data["balance"], errors="coerce")

    if "counterparty" not in data.columns:
        data["counterparty"] = ""

    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data = data.dropna(subset=["date"])
    data["amount"] = data["income"] - data["expense"]

    return data


def read_invoice_detail(file_path: str) -> pd.DataFrame:
    df = read_excel(file_path)

    mapping = {}
    for field in ["invoice_date", "invoice_number", "invoice_type", "amount",
                   "company", "goods_or_service", "tax_amount", "tax_rate"]:
        col = _smart_match_column(df, field)
        if col:
            mapping[col] = field

    if mapping:
        df = df.rename(columns=mapping)

    if "invoice_date" not in df.columns and "date" in df.columns:
        df = df.rename(columns={"date": "invoice_date"})

    required = ["invoice_date", "amount", "company"]
    for field in required:
        if field not in df.columns:
            raise ValueError(f"无法识别'{field}'列，文件: {file_path}")

    df["invoice_date"] = pd.to_datetime(df["invoice_date"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

    if "tax_amount" in df.columns:
        df["tax_amount"] = pd.to_numeric(df["tax_amount"], errors="coerce").fillna(0)

    if "goods_or_service" not in df.columns:
        df["goods_or_service"] = ""

    if "invoice_type" not in df.columns:
        df["invoice_type"] = ""

    if "invoice_number" not in df.columns:
        df["invoice_number"] = ""

    return df


def get_column_info(df: pd.DataFrame) -> Dict[str, Any]:
    return {
        "columns": list(df.columns),
        "row_count": len(df),
        "dtypes": {str(k): str(v) for k, v in df.dtypes.items()},
    }
