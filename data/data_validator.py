from typing import List, Optional, Tuple

import pandas as pd


def validate_bank_statement(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    errors = []

    if df.empty:
        errors.append("数据为空")
        return False, errors

    required_cols = ["交易日期", "摘要"]
    for col in required_cols:
        if col not in df.columns:
            errors.append(f"缺少必要列: {col}")

    amount_cols = []
    if "收入金额" in df.columns:
        amount_cols.append("收入金额")
    if "支出金额" in df.columns:
        amount_cols.append("支出金额")

    if not amount_cols:
        errors.append("缺少金额列（收入金额/支出金额）")

    if "交易日期" in df.columns:
        null_dates = df["交易日期"].isna().sum()
        if null_dates > 0:
            errors.append(f"有 {null_dates} 条记录缺少交易日期")

    for col in amount_cols:
        if col in df.columns:
            non_numeric = pd.to_numeric(df[col], errors="coerce").isna() & df[col].notna()
            if non_numeric.any():
                errors.append(f"列'{col}'包含非数值数据: {non_numeric.sum()} 条")

    if "收入金额" in df.columns and "支出金额" in df.columns:
        both_zero = (df["收入金额"].fillna(0) == 0) & (df["支出金额"].fillna(0) == 0)
        if both_zero.any():
            errors.append(f"有 {both_zero.sum()} 条记录收入和支出均为0")

    return len(errors) == 0, errors


def validate_invoice_detail(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    errors = []

    if df.empty:
        errors.append("发票数据为空")
        return False, errors

    required_cols = ["发票日期", "金额", "对方单位"]
    for col in required_cols:
        if col not in df.columns:
            errors.append(f"缺少必要列: {col}")

    if "金额" in df.columns:
        non_numeric = pd.to_numeric(df["金额"], errors="coerce").isna() & df["金额"].notna()
        if non_numeric.any():
            errors.append(f"金额列包含非数值数据: {non_numeric.sum()} 条")

        negative = pd.to_numeric(df["金额"], errors="coerce") < 0
        if negative.any():
            errors.append(f"有 {negative.sum()} 条发票金额为负数")

    return len(errors) == 0, errors


def validate_amount_balance(df: pd.DataFrame) -> Tuple[bool, Optional[str]]:
    if "收入金额" not in df.columns or "支出金额" not in df.columns:
        return True, None

    total_income = pd.to_numeric(df["收入金额"], errors="coerce").sum()
    total_expense = pd.to_numeric(df["支出金额"], errors="coerce").sum()
    net = total_income - total_expense

    if "余额" in df.columns and not df.empty:
        last_balance = pd.to_numeric(df["余额"].iloc[-1], errors="coerce")
        first_balance = pd.to_numeric(df["余额"].iloc[0], errors="coerce")
        if pd.notna(last_balance) and pd.notna(first_balance):
            expected_change = last_balance - first_balance
            if abs(net - expected_change) > 1:
                return False, (
                    f"金额合计校验不通过: 收支净额={net:.2f}, "
                    f"余额变动={expected_change:.2f}, 差异={abs(net - expected_change):.2f}"
                )

    return True, None
