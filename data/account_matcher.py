import re
from typing import Dict, List, Optional, Tuple

import pandas as pd
from fuzzywuzzy import fuzz


def _clean_company_name(name: str) -> str:
    if pd.isna(name) or not isinstance(name, str):
        return ""
    name = name.strip()
    suffixes = [
        "有限公司", "有限责任公司", "股份有限公司", "集团公司",
        "（有限合伙）", "(有限合伙)", "（普通合伙）", "(普通合伙)",
        "分公司", "办事处", "经营部", "门市部",
    ]
    for sfx in suffixes:
        name = name.replace(sfx, "")
    name = re.sub(r"[（()）\s\-_]", "", name)
    return name


def fuzzy_match_company(
    name: str,
    candidates: List[str],
    threshold: int = 80,
) -> Optional[Tuple[str, int]]:
    clean_name = _clean_company_name(name)
    if not clean_name:
        return None

    best_match = None
    best_score = 0

    for candidate in candidates:
        clean_candidate = _clean_company_name(candidate)
        if not clean_candidate:
            continue

        score = fuzz.token_sort_ratio(clean_name, clean_candidate)
        if score > best_score:
            best_score = score
            best_match = candidate

    if best_score >= threshold:
        return best_match, best_score
    return None


def match_bank_invoice(
    bank_df: pd.DataFrame,
    invoice_df: pd.DataFrame,
    match_threshold: int = 80,
    amount_tolerance: float = 10.0,
) -> pd.DataFrame:
    bank_companies = bank_df["对方单位"].dropna().unique().tolist()
    invoice_companies = invoice_df["对方单位"].dropna().unique().tolist()

    all_companies = set()
    company_map: Dict[str, List[str]] = {}

    for bc in bank_companies:
        match_result = fuzzy_match_company(bc, invoice_companies, match_threshold)
        if match_result:
            matched_name, _ = match_result
            key = matched_name
        else:
            key = bc
        all_companies.add(key)
        company_map.setdefault(key, []).append(("bank", bc))

    for ic in invoice_companies:
        match_result = fuzzy_match_company(ic, bank_companies, match_threshold)
        if match_result:
            matched_name, _ = match_result
            key = matched_name
        else:
            key = ic
        all_companies.add(key)
        company_map.setdefault(key, []).append(("invoice", ic))

    rows = []
    for company_key in sorted(all_companies):
        entries = company_map.get(company_key, [])
        bank_names = [e[1] for e in entries if e[0] == "bank"]
        invoice_names = [e[1] for e in entries if e[0] == "invoice"]

        bank_total_income = 0.0
        bank_total_expense = 0.0
        bank_details = []
        for bn in bank_names:
            subset = bank_df[bank_df["对方单位"] == bn]
            bank_total_income += pd.to_numeric(subset["收入金额"], errors="coerce").sum()
            bank_total_expense += pd.to_numeric(subset["支出金额"], errors="coerce").sum()
            for _, row in subset.iterrows():
                bank_details.append({
                    "date": str(row.get("交易日期", "")),
                    "description": str(row.get("摘要", "")),
                    "amount": float(pd.to_numeric(row.get("收入金额", 0), errors="coerce") or 0)
                              - float(pd.to_numeric(row.get("支出金额", 0), errors="coerce") or 0),
                })

        invoice_total = 0.0
        invoice_details = []
        for inv_name in invoice_names:
            subset = invoice_df[invoice_df["对方单位"] == inv_name]
            invoice_total += pd.to_numeric(subset["金额"], errors="coerce").sum()
            for _, row in subset.iterrows():
                invoice_details.append({
                    "date": str(row.get("发票日期", "")),
                    "number": str(row.get("发票号码", "")),
                    "amount": float(pd.to_numeric(row.get("金额", 0), errors="coerce") or 0),
                    "goods": str(row.get("货物或服务名称", "")),
                })

        bank_net = bank_total_income - bank_total_expense
        has_bank = len(bank_names) > 0
        has_invoice = len(invoice_names) > 0

        if has_bank and has_invoice:
            if abs(abs(bank_net) - invoice_total) <= amount_tolerance:
                if bank_net > 0:
                    status = "RECEIVED_MATCHED"
                    suggestion = "已收款+已开票，已平账"
                else:
                    status = "PAID_MATCHED"
                    suggestion = "已付款+已收票，已平账"
            else:
                if bank_net > 0:
                    status = "RECEIVED_NEED_INVOICE"
                    suggestion = f"已收款{bank_net:.2f}，发票{invoice_total:.2f}，金额不匹配，需核对"
                else:
                    status = "PAY_NEED_INVOICE"
                    suggestion = f"已付款{abs(bank_net):.2f}，发票{invoice_total:.2f}，金额不匹配，需核对"
        elif has_bank and not has_invoice:
            if bank_net > 0:
                status = "RECEIVED_NO_INVOICE"
                suggestion = f"已收款{bank_net:.2f}，无对应发票，提醒开票"
            else:
                status = "PAYMENT_NO_INVOICE"
                suggestion = f"已付款{abs(bank_net):.2f}，无对应发票，提醒索要发票"
        elif not has_bank and has_invoice:
            status = "INVOICE_NO_PAYMENT"
            suggestion = f"有发票{invoice_total:.2f}，无银行流水，需制作凭证"
        else:
            status = "NO_DATA"
            suggestion = "无数据"

        rows.append({
            "对方单位": company_key,
            "银行流水收入": bank_total_income,
            "银行流水支出": bank_total_expense,
            "银行流水净额": bank_net,
            "发票金额": invoice_total,
            "状态": status,
            "处理建议": suggestion,
            "银行流水明细": str(bank_details) if bank_details else "",
            "发票明细": str(invoice_details) if invoice_details else "",
        })

    result_df = pd.DataFrame(rows)

    status_order = {
        "RECEIVED_NEED_INVOICE": 0,
        "PAYMENT_NO_INVOICE": 1,
        "INVOICE_NO_PAYMENT": 2,
        "RECEIVED_NO_INVOICE": 3,
        "PAY_NEED_INVOICE": 4,
        "RECEIVED_MATCHED": 5,
        "PAID_MATCHED": 6,
        "NO_DATA": 7,
    }
    result_df["_sort"] = result_df["状态"].map(status_order).fillna(99)
    result_df = result_df.sort_values("_sort").drop(columns=["_sort"])

    return result_df.reset_index(drop=True)


def get_pending_items(match_result: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    pending = {}

    need_invoice = match_result[match_result["状态"].isin([
        "RECEIVED_NEED_INVOICE", "RECEIVED_NO_INVOICE"
    ])]
    if not need_invoice.empty:
        pending["需开票提醒"] = need_invoice

    need_collect = match_result[match_result["状态"].isin([
        "PAYMENT_NO_INVOICE", "PAY_NEED_INVOICE"
    ])]
    if not need_collect.empty:
        pending["需索要发票"] = need_collect

    need_voucher = match_result[match_result["状态"] == "INVOICE_NO_PAYMENT"]
    if not need_voucher.empty:
        pending["需制作凭证"] = need_voucher

    return pending
