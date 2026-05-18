from typing import Dict, Optional

import pandas as pd


def generate_balance_sheet(
    cash_and_equivalents: float = 0,
    accounts_receivable: float = 0,
    inventory: float = 0,
    fixed_assets: float = 0,
    accounts_payable: float = 0,
    taxes_payable: float = 0,
    paid_in_capital: float = 0,
    retained_earnings: float = 0,
    current_profit: float = 0,
) -> pd.DataFrame:
    current_assets = cash_and_equivalents + accounts_receivable + inventory
    non_current_assets = fixed_assets
    total_assets = current_assets + non_current_assets

    current_liabilities = accounts_payable + taxes_payable
    total_liabilities = current_liabilities

    total_equity = paid_in_capital + retained_earnings + current_profit

    rows = [
        {"项目": "流动资产", "行次": "", "期末余额": "", "年初余额": ""},
        {"项目": "  货币资金", "行次": 1, "期末余额": round(cash_and_equivalents, 2)},
        {"项目": "  应收账款", "行次": 2, "期末余额": round(accounts_receivable, 2)},
        {"项目": "  存货", "行次": 3, "期末余额": round(inventory, 2)},
        {"项目": "流动资产合计", "行次": 4, "期末余额": round(current_assets, 2)},
        {"项目": "", "行次": "", "期末余额": ""},
        {"项目": "非流动资产", "行次": "", "期末余额": ""},
        {"项目": "  固定资产", "行次": 5, "期末余额": round(fixed_assets, 2)},
        {"项目": "非流动资产合计", "行次": 6, "期末余额": round(non_current_assets, 2)},
        {"项目": "", "行次": "", "期末余额": ""},
        {"项目": "资产总计", "行次": 7, "期末余额": round(total_assets, 2)},
        {"项目": "", "行次": "", "期末余额": ""},
        {"项目": "流动负债", "行次": "", "期末余额": ""},
        {"项目": "  应付账款", "行次": 8, "期末余额": round(accounts_payable, 2)},
        {"项目": "  应交税费", "行次": 9, "期末余额": round(taxes_payable, 2)},
        {"项目": "流动负债合计", "行次": 10, "期末余额": round(current_liabilities, 2)},
        {"项目": "", "行次": "", "期末余额": ""},
        {"项目": "负债合计", "行次": 11, "期末余额": round(total_liabilities, 2)},
        {"项目": "", "行次": "", "期末余额": ""},
        {"项目": "所有者权益", "行次": "", "期末余额": ""},
        {"项目": "  实收资本", "行次": 12, "期末余额": round(paid_in_capital, 2)},
        {"项目": "  未分配利润", "行次": 13, "期末余额": round(retained_earnings + current_profit, 2)},
        {"项目": "所有者权益合计", "行次": 14, "期末余额": round(total_equity, 2)},
        {"项目": "", "行次": "", "期末余额": ""},
        {"项目": "负债和所有者权益总计", "行次": 15, "期末余额": round(total_liabilities + total_equity, 2)},
    ]

    return pd.DataFrame(rows)


def generate_income_statement(
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
    gross_profit = revenue - cost_of_goods
    operating_profit = gross_profit - admin_expenses - selling_expenses - financial_expenses - tax_surtax
    total_profit = operating_profit + other_income - other_expense
    net_profit = total_profit - income_tax

    rows = [
        {"项目": "一、营业收入", "本月数": round(revenue, 2), "本年累计": ""},
        {"项目": "减：营业成本", "本月数": round(cost_of_goods, 2), "本年累计": ""},
        {"项目": "    税金及附加", "本月数": round(tax_surtax, 2), "本年累计": ""},
        {"项目": "    管理费用", "本月数": round(admin_expenses, 2), "本年累计": ""},
        {"项目": "    销售费用", "本月数": round(selling_expenses, 2), "本年累计": ""},
        {"项目": "    财务费用", "本月数": round(financial_expenses, 2), "本年累计": ""},
        {"项目": "二、营业利润", "本月数": round(operating_profit, 2), "本年累计": ""},
        {"项目": "加：营业外收入", "本月数": round(other_income, 2), "本年累计": ""},
        {"项目": "减：营业外支出", "本月数": round(other_expense, 2), "本年累计": ""},
        {"项目": "三、利润总额", "本月数": round(total_profit, 2), "本年累计": ""},
        {"项目": "减：所得税费用", "本月数": round(income_tax, 2), "本年累计": ""},
        {"项目": "四、净利润", "本月数": round(net_profit, 2), "本年累计": ""},
    ]

    return pd.DataFrame(rows)
