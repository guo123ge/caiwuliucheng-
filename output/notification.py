from typing import Dict, List

import pandas as pd


def generate_notifications(
    match_result: pd.DataFrame,
    pending_review_count: int = 0,
) -> List[str]:
    notifications = []

    if pending_review_count > 0:
        notifications.append(f"⚠ 有 {pending_review_count} 条分类结果置信度较低，需要人工确认")

    if match_result is not None and not match_result.empty and "状态" in match_result.columns:
        need_invoice = match_result[match_result["状态"].isin([
            "RECEIVED_NEED_INVOICE", "RECEIVED_NO_INVOICE"
        ])]
        if not need_invoice.empty:
            companies = need_invoice["对方单位"].tolist()
            notifications.append(
                f"📝 需向以下单位开具发票 ({len(need_invoice)}家): {', '.join(companies[:5])}"
                + ("..." if len(companies) > 5 else "")
            )

        need_collect = match_result[match_result["状态"].isin([
            "PAYMENT_NO_INVOICE", "PAY_NEED_INVOICE"
        ])]
        if not need_collect.empty:
            companies = need_collect["对方单位"].tolist()
            notifications.append(
                f"📋 需向以下单位索要发票 ({len(need_collect)}家): {', '.join(companies[:5])}"
                + ("..." if len(companies) > 5 else "")
            )

        need_voucher = match_result[match_result["状态"] == "INVOICE_NO_PAYMENT"]
        if not need_voucher.empty:
            notifications.append(
                f"📄 有 {len(need_voucher)} 条发票无对应银行流水，已生成记账凭证"
            )

    return notifications


def print_notifications(notifications: List[str]):
    if not notifications:
        print("✅ 无待处理事项")
        return

    print("\n" + "=" * 60)
    print("  📌 待处理事项提醒")
    print("=" * 60)
    for i, note in enumerate(notifications, 1):
        print(f"  {i}. {note}")
    print("=" * 60 + "\n")


def save_notifications(notifications: List[str], output_path: str):
    if not notifications:
        return

    df = pd.DataFrame({"待处理事项": notifications})
    from data.excel_writer import save_dataframe
    save_dataframe(df, output_path, title="待处理事项提醒")
