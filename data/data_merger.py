import glob
from pathlib import Path
from typing import List, Optional

import pandas as pd

from data.excel_reader import read_bank_statement


def find_bank_statement_files(data_dir: str, year: int, month: int) -> List[str]:
    patterns = [
        str(Path(data_dir) / f"银行流水_*_{year}年{month:02d}月.xlsx"),
        str(Path(data_dir) / f"银行流水_*_{year}年{month:02d}月.xls"),
        str(Path(data_dir) / f"银行流水_*_{year}{month:02d}.xlsx"),
        str(Path(data_dir) / f"银行流水_*_{year}{month:02d}.xls"),
        str(Path(data_dir) / f"*银行流水*.xlsx"),
        str(Path(data_dir) / f"*银行流水*.xls"),
        str(Path(data_dir) / f"*{year}*{month:02d}*.xlsx"),
        str(Path(data_dir) / f"*{year}*{month:02d}*.xls"),
        str(Path(data_dir) / f"*{year}*{month}*.xlsx"),
        str(Path(data_dir) / f"*{year}*{month}*.xls"),
    ]

    files = []
    for pattern in patterns:
        files.extend(glob.glob(pattern))

    if not files:
        fallback = [
            str(Path(data_dir) / f"*银行流水*.xlsx"),
            str(Path(data_dir) / f"*银行流水*.xls"),
            str(Path(data_dir) / f"*.xlsx"),
            str(Path(data_dir) / f"*.xls"),
        ]
        for pattern in fallback:
            files.extend(glob.glob(pattern))

    seen = set()
    unique = []
    for f in files:
        if f not in seen:
            seen.add(f)
            unique.append(f)
    return sorted(unique)


def extract_bank_name(file_path: str) -> str:
    name = Path(file_path).stem
    if "工商" in name or "工行" in name:
        return "工商银行"
    elif "建设" in name or "建行" in name:
        return "建设银行"
    elif "农业" in name or "农行" in name:
        return "农业银行"
    elif "中国银行" in name or "中行" in name:
        return "中国银行"
    elif "交通" in name or "交行" in name:
        return "交通银行"
    elif "招商" in name:
        return "招商银行"
    elif "浦发" in name:
        return "浦发银行"
    elif "中信" in name:
        return "中信银行"
    elif "民生" in name:
        return "民生银行"
    elif "兴业" in name:
        return "兴业银行"
    elif "光大" in name:
        return "光大银行"
    elif "平安" in name:
        return "平安银行"
    elif "邮储" in name or "邮政" in name:
        return "邮储银行"
    return "其他银行"


def merge_bank_statements(
    data_dir: str, year: int, month: int
) -> pd.DataFrame:
    files = find_bank_statement_files(data_dir, year, month)

    if not files:
        raise FileNotFoundError(
            f"在 {data_dir} 中未找到 {year}年{month}月 的银行流水文件"
        )

    dfs = []
    for f in files:
        df = read_bank_statement(f)
        bank_name = extract_bank_name(f)
        df["银行"] = bank_name
        df["源文件"] = Path(f).name
        dfs.append(df)

    merged = pd.concat(dfs, ignore_index=True)
    merged = merged.sort_values("date").reset_index(drop=True)

    return merged


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    std_cols = {
        "date": "交易日期",
        "description": "摘要",
        "income": "收入金额",
        "expense": "支出金额",
        "balance": "余额",
        "counterparty": "对方单位",
        "amount": "净额",
    }

    rename_map = {}
    for old, new in std_cols.items():
        if old in df.columns:
            rename_map[old] = new

    df = df.rename(columns=rename_map)

    column_order = [v for v in std_cols.values() if v in df.columns]
    extra_cols = [c for c in df.columns if c not in column_order]
    return df[column_order + extra_cols]
