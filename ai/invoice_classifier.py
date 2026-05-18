from typing import Dict, List, Optional, Tuple

import pandas as pd

from ai.classification_cache import lookup, store, store_batch
from ai.llm_client import llm_client
from config import config


def _keyword_match_invoice(row: pd.Series) -> Optional[Tuple[str, float]]:
    goods = str(row.get("货物或服务名称", row.get("goods_or_service", ""))).strip()
    memo = str(row.get("备注", row.get("memo", ""))).strip()
    combined = f"{goods} {memo}"

    if not combined.strip():
        return None

    categories = config.invoice_categories
    for cat_name, cat_info in sorted(categories.items(), key=lambda x: x[1].get("priority", 99)):
        keywords = cat_info.get("keywords", [])
        for kw in keywords:
            if kw in combined:
                return cat_name, 0.95

    return None


def _classify_invoice_single_rule_first(row: pd.Series) -> Dict:
    goods = str(row.get("货物或服务名称", row.get("goods_or_service", ""))).strip()
    memo = str(row.get("备注", row.get("memo", ""))).strip()
    cache_text = f"{goods}|{memo}"

    cached = lookup(cache_text)
    if cached:
        return {
            "category": cached["category"],
            "confidence": cached["confidence"],
            "reason": cached.get("reason", "(缓存命中)"),
            "method": "cache",
        }

    kw_result = _keyword_match_invoice(row)
    if kw_result:
        cat, conf = kw_result
        store(cache_text, cat, conf, "关键词匹配", "keyword")
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


def classify_invoices(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "发票分类" not in df.columns:
        df["发票分类"] = None
    if "分类置信度" not in df.columns:
        df["分类置信度"] = 0.0
    if "分类方法" not in df.columns:
        df["分类方法"] = ""
    if "分类理由" not in df.columns:
        df["分类理由"] = ""

    pending_indices = []
    for idx, row in df.iterrows():
        result = _classify_invoice_single_rule_first(row)
        if result["category"] is not None:
            df.at[idx, "发票分类"] = result["category"]
            df.at[idx, "分类置信度"] = result["confidence"]
            df.at[idx, "分类方法"] = result["method"]
            df.at[idx, "分类理由"] = result["reason"]
        else:
            pending_indices.append(idx)

    if not pending_indices:
        return df

    threshold = config.llm_threshold
    max_batch = threshold.get("max_batch_size", 50)

    categories = list(config.invoice_categories.keys())
    cat_descriptions = {
        cat: ", ".join(info.get("keywords", [])[:5])
        for cat, info in config.invoice_categories.items()
    }

    for batch_start in range(0, len(pending_indices), max_batch):
        batch_indices = pending_indices[batch_start:batch_start + max_batch]
        items = []
        for idx in batch_indices:
            row = df.loc[idx]
            items.append({
                "发票日期": str(row.get("发票日期", row.get("invoice_date", ""))),
                "发票号码": str(row.get("发票号码", row.get("invoice_number", ""))),
                "发票类型": str(row.get("发票类型", row.get("invoice_type", ""))),
                "金额": str(row.get("金额", row.get("amount", ""))),
                "对方单位": str(row.get("对方单位", row.get("company", ""))),
                "货物或服务": str(row.get("货物或服务名称", row.get("goods_or_service", ""))),
                "备注": str(row.get("备注", row.get("memo", ""))),
            })

        try:
            results = llm_client.classify_batch(items, categories, cat_descriptions)
        except Exception as e:
            for idx in batch_indices:
                df.at[idx, "发票分类"] = "其他"
                df.at[idx, "分类置信度"] = 0.0
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

                df.at[df_idx, "发票分类"] = category
                df.at[df_idx, "分类置信度"] = confidence
                df.at[df_idx, "分类方法"] = "llm"
                df.at[df_idx, "分类理由"] = result.get("reason", "")

                row = df.loc[df_idx]
                goods = str(row.get("货物或服务名称", row.get("goods_or_service", ""))).strip()
                memo = str(row.get("备注", row.get("memo", ""))).strip()
                cache_text = f"{goods}|{memo}"
                cache_batch.append((cache_text, category, confidence, result.get("reason", "")))

        if cache_batch:
            store_batch(cache_batch)

    min_conf = threshold.get("min_confidence", 0.7)
    low_conf_mask = (
        (df["分类方法"] == "llm") &
        (pd.to_numeric(df["分类置信度"], errors="coerce") < min_conf)
    )
    df.loc[low_conf_mask, "发票分类"] = df.loc[low_conf_mask, "发票分类"].apply(
        lambda x: f"{x}(待确认)"
    )

    return df


def get_invoice_summary(df: pd.DataFrame) -> pd.DataFrame:
    if "发票分类" not in df.columns:
        return pd.DataFrame()

    summary_rows = []
    for cat_name in df["发票分类"].dropna().unique():
        subset = df[df["发票分类"] == cat_name]
        total_amount = pd.to_numeric(subset["金额"], errors="coerce").sum() if "金额" in subset.columns else 0.0
        total_tax = pd.to_numeric(subset["税额"], errors="coerce").sum() if "税额" in subset.columns else 0.0
        summary_rows.append({
            "发票分类": cat_name,
            "发票数量": len(subset),
            "金额合计": total_amount,
            "税额合计": total_tax,
        })

    summary_df = pd.DataFrame(summary_rows)
    if not summary_df.empty:
        total_row = {
            "发票分类": "合计",
            "发票数量": summary_df["发票数量"].sum(),
            "金额合计": summary_df["金额合计"].sum(),
            "税额合计": summary_df["税额合计"].sum(),
        }
        summary_df = pd.concat(
            [summary_df, pd.DataFrame([total_row])], ignore_index=True
        )

    return summary_df
