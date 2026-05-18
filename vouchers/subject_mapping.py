from typing import Dict, Optional

from config import config


def get_subject_for_category(category: str) -> Optional[Dict]:
    clean_cat = category.replace("(待确认)", "").strip()
    return config.get_subject_for_category(clean_cat)


def get_subject_for_invoice_category(category: str) -> Optional[Dict]:
    clean_cat = category.replace("(待确认)", "").strip()
    return config.get_invoice_subject(clean_cat)


def get_debit_subject(category: str, is_invoice: bool = False) -> Optional[Dict]:
    if is_invoice:
        mapping = get_subject_for_invoice_category(category)
    else:
        mapping = get_subject_for_category(category)

    if mapping:
        return {
            "name": mapping.get("debit", ""),
            "code": mapping.get("debit_code", ""),
        }
    return None


def get_credit_subject(category: str, is_invoice: bool = False) -> Optional[Dict]:
    if is_invoice:
        mapping = get_subject_for_invoice_category(category)
    else:
        mapping = get_subject_for_category(category)

    if mapping:
        return {
            "name": mapping.get("credit", ""),
            "code": mapping.get("credit_code", ""),
        }
    return None


def get_full_mapping(category: str, is_invoice: bool = False) -> Optional[Dict]:
    if is_invoice:
        return get_subject_for_invoice_category(category)
    return get_subject_for_category(category)
