from pathlib import Path
from typing import List, Optional

import pandas as pd

from data.excel_writer import save_dataframe


def save_report(
    df: pd.DataFrame,
    output_path: str,
    title: Optional[str] = None,
):
    save_dataframe(df, output_path, title=title)


def save_multiple_reports(
    reports: List[dict],
    output_dir: str,
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for report in reports:
        df = report.get("dataframe")
        filename = report.get("filename", "report.xlsx")
        title = report.get("title")
        if df is not None and not df.empty:
            save_dataframe(df, str(output_dir / filename), title=title)
