from typing import Dict, Tuple

import pandas as pd


def calculate_profit(
    revenue: float = 0,
    cost_of_goods: float = 0,
    admin_expenses: float = 0,
    selling_expenses: float = 0,
    financial_expenses: float = 0,
    tax_surtax: float = 0,
    other_income: float = 0,
    other_expense: float = 0,
) -> Dict:
    gross_profit = revenue - cost_of_goods
    operating_expenses = admin_expenses + selling_expenses + financial_expenses + tax_surtax
    operating_profit = gross_profit - operating_expenses
    total_profit = operating_profit + other_income - other_expense

    return {
        "营业收入": round(revenue, 2),
        "减：营业成本": round(cost_of_goods, 2),
        "毛利润": round(gross_profit, 2),
        "减：管理费用": round(admin_expenses, 2),
        "减：销售费用": round(selling_expenses, 2),
        "减：财务费用": round(financial_expenses, 2),
        "减：税金及附加": round(tax_surtax, 2),
        "营业利润": round(operating_profit, 2),
        "加：营业外收入": round(other_income, 2),
        "减：营业外支出": round(other_expense, 2),
        "利润总额": round(total_profit, 2),
    }


def aggregate_from_classified(
    bank_summary: pd.DataFrame,
    invoice_summary: pd.DataFrame,
) -> Dict:
    revenue = 0.0
    cost_of_goods = 0.0
    admin_expenses = 0.0
    financial_expenses = 0.0
    other_income = 0.0
    other_expense = 0.0

    if not bank_summary.empty and "分类" in bank_summary.columns:
        for _, row in bank_summary.iterrows():
            cat = str(row.get("分类", ""))
            net = float(row.get("净额", 0) or 0)

            if "收回货款" in cat:
                revenue += abs(net) if net > 0 else 0
            elif "转付货款" in cat:
                cost_of_goods += abs(net) if net < 0 else 0
            elif "员工工资" in cat or "员工社保" in cat:
                admin_expenses += abs(net) if net < 0 else 0
            elif "银行手续费" in cat or "利息" in cat:
                financial_expenses += abs(net) if net < 0 else 0
            elif "公司缴税" in cat:
                pass
            elif "其他收入" in cat:
                other_income += net if net > 0 else 0
            elif "其他支出" in cat:
                other_expense += abs(net) if net < 0 else 0

    if not invoice_summary.empty and "发票分类" in invoice_summary.columns:
        for _, row in invoice_summary.iterrows():
            cat = str(row.get("发票分类", ""))
            amount = float(row.get("金额合计", 0) or 0)

            if "报销" in cat:
                admin_expenses += amount
            elif "抵减材料款" in cat:
                cost_of_goods += amount

    return {
        "revenue": revenue,
        "cost_of_goods": cost_of_goods,
        "admin_expenses": admin_expenses,
        "financial_expenses": financial_expenses,
        "other_income": other_income,
        "other_expense": other_expense,
    }


def generate_profit_statement(
    revenue: float = 0,
    cost_of_goods: float = 0,
    admin_expenses: float = 0,
    selling_expenses: float = 0,
    financial_expenses: float = 0,
    tax_surtax: float = 0,
    other_income: float = 0,
    other_expense: float = 0,
    income_tax: float = 0,
) -> pd.DataFrame:
    profit_data = calculate_profit(
        revenue, cost_of_goods, admin_expenses, selling_expenses,
        financial_expenses, tax_surtax, other_income, other_expense,
    )

    net_profit = profit_data["利润总额"] - income_tax

    rows = [
        {"项目": "一、营业收入", "行次": 1, "本月数": profit_data["营业收入"]},
        {"项目": "减：营业成本", "行次": 2, "本月数": profit_data["减：营业成本"]},
        {"项目": "二、毛利润", "行次": 3, "本月数": profit_data["毛利润"]},
        {"项目": "减：管理费用", "行次": 4, "本月数": profit_data["减：管理费用"]},
        {"项目": "减：销售费用", "行次": 5, "本月数": profit_data["减：销售费用"]},
        {"项目": "减：财务费用", "行次": 6, "本月数": profit_data["减：财务费用"]},
        {"项目": "减：税金及附加", "行次": 7, "本月数": profit_data["减：税金及附加"]},
        {"项目": "三、营业利润", "行次": 8, "本月数": profit_data["营业利润"]},
        {"项目": "加：营业外收入", "行次": 9, "本月数": profit_data["加：营业外收入"]},
        {"项目": "减：营业外支出", "行次": 10, "本月数": profit_data["减：营业外支出"]},
        {"项目": "四、利润总额", "行次": 11, "本月数": profit_data["利润总额"]},
        {"项目": "减：所得税费用", "行次": 12, "本月数": round(income_tax, 2)},
        {"项目": "五、净利润", "行次": 13, "本月数": round(net_profit, 2)},
    ]

    return pd.DataFrame(rows)
