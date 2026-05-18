from typing import Dict, Tuple

import pandas as pd

from config import config


def calculate_vat(
    output_invoice_total: float,
    output_invoice_tax: float,
    input_invoice_total: float,
    input_invoice_tax: float,
) -> Dict:
    rules = config.tax_rules.get("value_added_tax", {})

    output_tax = output_invoice_tax if output_invoice_tax > 0 else output_invoice_total * rules.get("general_tax_rate", 0.13)
    input_tax = input_invoice_tax if input_invoice_tax > 0 else input_invoice_total * rules.get("general_tax_rate", 0.13)

    payable = max(output_tax - input_tax, 0)

    return {
        "销项税额": round(output_tax, 2),
        "进项税额": round(input_tax, 2),
        "应缴增值税": round(payable, 2),
        "留抵税额": round(max(input_tax - output_tax, 0), 2),
    }


def calculate_surtax(vat_payable: float) -> Dict:
    rules = config.tax_rules.get("surtax", {})

    urban = vat_payable * rules.get("urban_construction", 0.07)
    education = vat_payable * rules.get("education", 0.03)
    local_education = vat_payable * rules.get("local_education", 0.02)

    return {
        "城建税": round(urban, 2),
        "教育费附加": round(education, 2),
        "地方教育附加": round(local_education, 2),
        "附加税合计": round(urban + education + local_education, 2),
    }


def calculate_corporate_income_tax(profit: float) -> Dict:
    rules = config.tax_rules.get("corporate_income_tax", {})

    if profit <= 0:
        rate = 0
    elif profit <= rules.get("small_micro_threshold_profit", 1000000):
        rate = rules.get("small_micro_rate", 0.05)
    elif profit <= rules.get("small_profit_threshold_profit", 3000000):
        rate = rules.get("small_profit_rate", 0.20)
    else:
        rate = rules.get("standard_rate", 0.25)

    tax = profit * rate

    return {
        "利润总额": round(profit, 2),
        "适用税率": rate,
        "应缴所得税": round(tax, 2),
    }


def calculate_stamp_duty(
    purchase_sales_amount: float = 0,
    loan_amount: float = 0,
    capital_amount: float = 0,
) -> Dict:
    rules = config.tax_rules.get("stamp_duty", {})

    purchase_sales_tax = purchase_sales_amount * rules.get("purchase_sale_contract", 0.0003)
    loan_tax = loan_amount * rules.get("loan_contract", 0.00005)
    capital_tax = capital_amount * rules.get("capital_account", 0.00025)

    total = purchase_sales_tax + loan_tax + capital_tax

    return {
        "购销合同印花税": round(purchase_sales_tax, 2),
        "借款合同印花税": round(loan_tax, 2),
        "资金账簿印花税": round(capital_tax, 2),
        "印花税合计": round(total, 2),
    }


def generate_tax_report(
    output_invoice_total: float = 0,
    output_invoice_tax: float = 0,
    input_invoice_total: float = 0,
    input_invoice_tax: float = 0,
    profit: float = 0,
    purchase_sales_amount: float = 0,
) -> pd.DataFrame:
    vat = calculate_vat(output_invoice_total, output_invoice_tax,
                         input_invoice_total, input_invoice_tax)
    surtax = calculate_surtax(vat["应缴增值税"])
    income_tax = calculate_corporate_income_tax(profit)
    stamp = calculate_stamp_duty(purchase_sales_amount)

    total_tax = (
        vat["应缴增值税"]
        + surtax["附加税合计"]
        + income_tax["应缴所得税"]
        + stamp["印花税合计"]
    )

    rows = [
        {"税种": "增值税", "计税依据": f"销项{vat['销项税额']} - 进项{vat['进项税额']}",
         "税率": "13%", "应纳税额": vat["应缴增值税"]},
        {"税种": "城建税", "计税依据": vat["应缴增值税"],
         "税率": "7%", "应纳税额": surtax["城建税"]},
        {"税种": "教育费附加", "计税依据": vat["应缴增值税"],
         "税率": "3%", "应纳税额": surtax["教育费附加"]},
        {"税种": "地方教育附加", "计税依据": vat["应缴增值税"],
         "税率": "2%", "应纳税额": surtax["地方教育附加"]},
        {"税种": "企业所得税", "计税依据": income_tax["利润总额"],
         "税率": f"{income_tax['适用税率']*100:.0f}%", "应纳税额": income_tax["应缴所得税"]},
        {"税种": "印花税", "计税依据": purchase_sales_amount,
         "税率": "0.03%", "应纳税额": stamp["印花税合计"]},
        {"税种": "合计", "计税依据": "", "税率": "", "应纳税额": round(total_tax, 2)},
    ]

    return pd.DataFrame(rows)
