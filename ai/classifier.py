import re
from typing import Dict, List, Optional, Tuple

import pandas as pd

from ai.classification_cache import lookup, store, store_batch
from ai.llm_client import llm_client
from config import config


def _keyword_match(description: str) -> Optional[Tuple[str, float]]:
    if not description or pd.isna(description):
        return None

    desc = str(description).strip()
    if not desc:
        return None

    categories = config.bank_categories
    for cat_name, cat_info in sorted(categories.items(), key=lambda x: x[1].get("priority", 99)):
        keywords = cat_info.get("keywords", [])
        for kw in keywords:
            if kw in desc:
                return cat_name, 0.95

    return None


def _classify_single_rule_first(description: str) -> Dict:
    cached = lookup(description)
    if cached:
        return {
            "category": cached["category"],
            "confidence": cached["confidence"],
            "reason": cached.get("reason", "(缓存命中)"),
            "method": "cache",
        }

    kw_result = _keyword_match(description)
    if kw_result:
        cat, conf = kw_result
        store(description, cat, conf, "关键词匹配", "keyword")
        return {
            "category": cat,
            "confidence": conf,
            "reason": "关键词匹配",
            "method": "keyword",
        }

    return {
        "category": None,
        "confidence": 0,
        "reason": "",
        "method": "pending",
    }


def classify_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "分类" not in df.columns:
        df["分类"] = None
    if "置信度" not in df.columns:
        df["置信度"] = 0.0
    if "分类方法" not in df.columns:
        df["分类方法"] = ""
    if "分类理由" not in df.columns:
        df["分类理由"] = ""

    pending_indices = []
    for idx, row in df.iterrows():
        desc = row.get("摘要", row.get("description", ""))
        if pd.isna(desc) or not isinstance(desc, str):
            desc = ""
        result = _classify_single_rule_first(desc)

        if result["category"] is not None:
            df.at[idx, "分类"] = result["category"]
            df.at[idx, "置信度"] = result["confidence"]
            df.at[idx, "分类方法"] = result["method"]
            df.at[idx, "分类理由"] = result["reason"]
        else:
            pending_indices.append(idx)

    if not pending_indices:
        return df

    threshold = config.llm_threshold
    max_batch = threshold.get("max_batch_size", 50)

    categories = list(config.bank_categories.keys())
    cat_descriptions = {
        cat: ", ".join(info.get("keywords", [])[:5])
        for cat, info in config.bank_categories.items()
    }

    for batch_start in range(0, len(pending_indices), max_batch):
        batch_indices = pending_indices[batch_start:batch_start + max_batch]
        items = []
        for idx in batch_indices:
            row = df.loc[idx]
            items.append({
                "日期": str(row.get("交易日期", row.get("date", ""))),
                "摘要": str(row.get("摘要", row.get("description", ""))),
                "收入": str(row.get("收入金额", row.get("income", ""))),
                "支出": str(row.get("支出金额", row.get("expense", ""))),
                "对方": str(row.get("对方单位", row.get("counterparty", ""))),
            })

        try:
            results = llm_client.classify_batch(items, categories, cat_descriptions)
        except Exception as e:
            for idx in batch_indices:
                df.at[idx, "分类"] = "其他"
                df.at[idx, "置信度"] = 0.0
                df.at[idx, "分类方法"] = "error"
                df.at[idx, "分类理由"] = f"LLM调用失败: {e}"
            continue

        cache_batch = []
        for result in results:
            item_idx = result.get("index", -1)
            if 0 <= item_idx < len(batch_indices):
                df_idx = batch_indices[item_idx]
                category = result.get("category", "其他")
                confidence = result.get("confidence", 0.0)

                df.at[df_idx, "分类"] = category
                df.at[df_idx, "置信度"] = confidence
                df.at[df_idx, "分类方法"] = "llm"
                df.at[df_idx, "分类理由"] = result.get("reason", "")

                desc = str(df.at[df_idx, "摘要"])
                cache_batch.append((desc, category, confidence, result.get("reason", "")))

        if cache_batch:
            store_batch(cache_batch)

    min_conf = threshold.get("min_confidence", 0.7)
    low_conf_mask = (
        (df["分类方法"] == "llm") &
        (pd.to_numeric(df["置信度"], errors="coerce") < min_conf)
    )
    df.loc[low_conf_mask, "分类"] = df.loc[low_conf_mask, "分类"].apply(
        lambda x: f"{x}(待确认)"
    )

    return df


def get_classification_summary(df: pd.DataFrame) -> pd.DataFrame:
    if "分类" not in df.columns:
        return pd.DataFrame()

    summary_rows = []
    for cat_name in df["分类"].dropna().unique():
        subset = df[df["分类"] == cat_name]
        total_income = pd.to_numeric(subset["收入金额"], errors="coerce").sum() if "收入金额" in subset.columns else 0.0
        total_expense = pd.to_numeric(subset["支出金额"], errors="coerce").sum() if "支出金额" in subset.columns else 0.0
        summary_rows.append({
            "分类": cat_name,
            "笔数": len(subset),
            "收入合计": total_income,
            "支出合计": total_expense,
            "净额": total_income - total_expense,
        })

    summary_df = pd.DataFrame(summary_rows)
    if not summary_df.empty:
        total_row = {
            "分类": "合计",
            "笔数": summary_df["笔数"].sum(),
            "收入合计": summary_df["收入合计"].sum(),
            "支出合计": summary_df["支出合计"].sum(),
            "净额": summary_df["净额"].sum(),
        }
        summary_df = pd.concat(
            [summary_df, pd.DataFrame([total_row])], ignore_index=True
        )

    return summary_df


def get_pending_review(df: pd.DataFrame) -> pd.DataFrame:
    if "分类" not in df.columns:
        return pd.DataFrame()
    return df[df["分类"].str.contains("待确认", na=False)].copy()
