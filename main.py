import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from config import config
from data.data_merger import merge_bank_statements, standardize_columns
from data.data_validator import validate_bank_statement, validate_invoice_detail
from data.excel_reader import read_invoice_detail
from data.account_matcher import match_bank_invoice, get_pending_items
from ai.classifier import classify_dataframe, get_classification_summary, get_pending_review
from ai.invoice_classifier import classify_invoices, get_invoice_summary
from calculations.tax_calculator import generate_tax_report
from calculations.profit_calculator import aggregate_from_classified, generate_profit_statement
from calculations.statement_generator import generate_balance_sheet, generate_income_statement
from vouchers.voucher_generator import (
    generate_bank_vouchers,
    generate_invoice_vouchers,
    generate_sales_vouchers,
)
from output.summary_writer import (
    save_classified_bank_statement,
    save_classified_invoices,
    save_match_result,
    save_vouchers,
    save_tax_report,
    save_financial_statements,
)
from output.notification import generate_notifications, print_notifications, save_notifications


def setup_logging():
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    logging.basicConfig(
        level=getattr(logging, config.log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return log_file


def wait_for_confirmation(message: str = "按 Enter 继续，输入 q 退出"):
    response = input(f"\n{message}: ").strip().lower()
    if response == "q":
        print("用户取消操作")
        sys.exit(0)


def step1_process_bank_statements(year: int, month: int):
    logging.info(f"=== 流程1: 银行流水处理 {year}年{month:02d}月 ===")

    raw_dir = config.data_dirs.get("raw_data", "../00_原始数据")
    logging.info(f"读取原始数据目录: {raw_dir}")

    merged = merge_bank_statements(raw_dir, year, month)
    logging.info(f"合并后共 {len(merged)} 条银行流水记录")

    valid, errors = validate_bank_statement(merged)
    if not valid:
        for err in errors:
            logging.warning(f"数据校验警告: {err}")

    logging.info("开始AI分类...")
    classified = classify_dataframe(merged)

    cache_hits = len(classified[classified["分类方法"] == "cache"])
    keyword_hits = len(classified[classified["分类方法"] == "keyword"])
    llm_calls = len(classified[classified["分类方法"] == "llm"])
    logging.info(
        f"分类完成: 缓存命中{cache_hits}, 关键词匹配{keyword_hits}, LLM分类{llm_calls}"
    )

    summary = get_classification_summary(classified)
    pending = get_pending_review(classified)

    classified_dir = config.data_dirs.get("classified", "../01_分类汇总")
    output_path = str(
        Path(classified_dir) / f"银行流水分类汇总_{year}年{month:02d}月.xlsx"
    )
    save_classified_bank_statement(classified, summary, output_path)
    logging.info(f"分类结果已保存: {output_path}")

    if not pending.empty:
        logging.warning(f"有 {len(pending)} 条记录需要人工确认")
        print(f"\n⚠ 有 {len(pending)} 条记录置信度较低，请打开分类汇总表审核'待确认'条目")

    return classified, summary


def step2_process_invoices(year: int, month: int, bank_classified: None = None):
    logging.info(f"=== 流程2: 发票处理与关联 {year}年{month:02d}月 ===")

    raw_dir = config.data_dirs.get("raw_data", "../00_原始数据")
    logging.info(f"读取发票数据目录: {raw_dir}")

    import glob
    invoice_patterns = [
        str(Path(raw_dir) / f"发票明细_*_{year}年{month:02d}月.xlsx"),
        str(Path(raw_dir) / f"发票明细_*_{year}{month:02d}.xlsx"),
    ]
    invoice_files = []
    for pattern in invoice_patterns:
        invoice_files.extend(glob.glob(pattern))

    if not invoice_files:
        logging.warning("未找到发票明细文件，跳过发票处理")
        return None, None, None

    invoice_dfs = []
    for f in invoice_files:
        df = read_invoice_detail(f)
        df["源文件"] = Path(f).name
        invoice_dfs.append(df)

    invoices = pd.concat(invoice_dfs, ignore_index=True) if invoice_dfs else None
    if invoices is None or invoices.empty:
        logging.warning("发票数据为空")
        return None, None, None

    import pandas as pd
    logging.info(f"共读取 {len(invoices)} 条发票记录")

    valid, errors = validate_invoice_detail(invoices)
    if not valid:
        for err in errors:
            logging.warning(f"发票数据校验警告: {err}")

    logging.info("开始发票分类...")
    classified_invoices = classify_invoices(invoices)
    invoice_summary = get_invoice_summary(classified_invoices)

    classified_dir = config.data_dirs.get("classified", "../01_分类汇总")
    invoice_output = str(
        Path(classified_dir) / f"发票分类汇总_{year}年{month:02d}月.xlsx"
    )
    save_classified_invoices(classified_invoices, invoice_summary, invoice_output)
    logging.info(f"发票分类结果已保存: {invoice_output}")

    logging.info("开始账户-发票关联分析...")
    match_result = match_bank_invoice(bank_classified, classified_invoices)
    pending_items = get_pending_items(match_result)

    matched_dir = config.data_dirs.get("matched", "../02_关联分析")
    match_output = str(
        Path(matched_dir) / f"账户-发票关联表_{year}年{month:02d}月.xlsx"
    )
    save_match_result(match_result, pending_items, match_output)
    logging.info(f"关联分析结果已保存: {match_output}")

    return classified_invoices, invoice_summary, match_result


def step3_tax_calculation(
    year: int, month: int,
    invoice_summary: None = None,
    profit: float = 0,
):
    logging.info(f"=== 流程3: 税务测算 {year}年{month:02d}月 ===")

    output_invoice_total = 0
    output_invoice_tax = 0
    input_invoice_total = 0
    input_invoice_tax = 0

    if invoice_summary is not None and not invoice_summary.empty:
        for _, row in invoice_summary.iterrows():
            cat = str(row.get("发票分类", ""))
            amount = float(row.get("金额合计", 0) or 0)
            tax = float(row.get("税额合计", 0) or 0)
            if "抵减材料款" in cat or "报销" in cat or "固定资产" in cat:
                input_invoice_total += amount
                input_invoice_tax += tax
            else:
                output_invoice_total += amount
                output_invoice_tax += tax

    tax_report = generate_tax_report(
        output_invoice_total=output_invoice_total,
        output_invoice_tax=output_invoice_tax,
        input_invoice_total=input_invoice_total,
        input_invoice_tax=input_invoice_tax,
        profit=profit,
        purchase_sales_amount=input_invoice_total + output_invoice_total,
    )

    reports_dir = config.data_dirs.get("reports", "../04_税务报表")
    tax_output = str(
        Path(reports_dir) / f"当月税务测算表_{year}年{month:02d}月.xlsx"
    )
    save_tax_report(tax_report, tax_output)
    logging.info(f"税务测算表已保存: {tax_output}")

    total_tax = float(tax_report[tax_report["税种"] == "合计"]["应纳税额"].values[0])
    logging.info(f"当月应缴税费合计: {total_tax:.2f}")

    return tax_report


def step4_profit_calculation(
    year: int, month: int,
    bank_summary: None = None,
    invoice_summary: None = None,
):
    logging.info(f"=== 流程4: 利润核算 {year}年{month:02d}月 ===")

    aggregated = aggregate_from_classified(bank_summary, invoice_summary)

    profit_statement = generate_profit_statement(
        revenue=aggregated["revenue"],
        cost_of_goods=aggregated["cost_of_goods"],
        admin_expenses=aggregated["admin_expenses"],
        financial_expenses=aggregated["financial_expenses"],
        other_income=aggregated["other_income"],
        other_expense=aggregated["other_expense"],
    )

    profit = float(
        profit_statement[profit_statement["项目"] == "四、利润总额"]["本月数"].values[0]
    )
    logging.info(f"本月利润总额: {profit:.2f}")

    return profit_statement, profit, aggregated


def step5_financial_statements(
    year: int, month: int,
    profit_statement: None = None,
    aggregated: dict = None,
    tax_report: None = None,
):
    logging.info(f"=== 流程5: 财务报表生成 {year}年{month:02d}月 ===")

    revenue = aggregated.get("revenue", 0)
    cost_of_goods = aggregated.get("cost_of_goods", 0)
    admin_expenses = aggregated.get("admin_expenses", 0)
    financial_expenses = aggregated.get("financial_expenses", 0)
    other_income = aggregated.get("other_income", 0)
    other_expense = aggregated.get("other_expense", 0)

    income_tax = 0
    if tax_report is not None and not tax_report.empty:
        tax_row = tax_report[tax_report["税种"] == "企业所得税"]
        if not tax_row.empty:
            income_tax = float(tax_row["应纳税额"].values[0])

    balance_sheet = generate_balance_sheet(
        cash_and_equivalents=0,
        accounts_receivable=revenue * 0.3,
        inventory=cost_of_goods * 0.5,
        fixed_assets=0,
        accounts_payable=cost_of_goods * 0.3,
        taxes_payable=income_tax,
        paid_in_capital=0,
        retained_earnings=0,
        current_profit=float(
            profit_statement[profit_statement["项目"] == "四、利润总额"]["本月数"].values[0]
        ) - income_tax if profit_statement is not None else 0,
    )

    income_statement = generate_income_statement(
        revenue=revenue,
        cost_of_goods=cost_of_goods,
        admin_expenses=admin_expenses,
        financial_expenses=financial_expenses,
        other_income=other_income,
        other_expense=other_expense,
        income_tax=income_tax,
    )

    reports_dir = config.data_dirs.get("reports", "../04_税务报表")
    save_financial_statements(balance_sheet, income_statement, reports_dir)
    logging.info(f"财务报表已保存至: {reports_dir}")

    return balance_sheet, income_statement


def run_all(year: int, month: int):
    log_file = setup_logging()
    logging.info(f"开始执行全流程: {year}年{month:02d}月")
    logging.info(f"日志文件: {log_file}")

    try:
        bank_classified, bank_summary = step1_process_bank_statements(year, month)
        wait_for_confirmation("流程1完成，请审核分类结果后按 Enter 继续")

        classified_invoices, invoice_summary, match_result = step2_process_invoices(
            year, month, bank_classified
        )
        if classified_invoices is not None:
            wait_for_confirmation("流程2完成，请审核发票分类和关联结果后按 Enter 继续")

        profit_statement, profit, aggregated = step4_profit_calculation(
            year, month, bank_summary, invoice_summary
        )

        tax_report = step3_tax_calculation(year, month, invoice_summary, profit)

        balance_sheet, income_statement = step5_financial_statements(
            year, month, profit_statement, aggregated, tax_report
        )

        bank_vouchers = generate_bank_vouchers(bank_classified)
        invoice_vouchers = (
            generate_invoice_vouchers(classified_invoices)
            if classified_invoices is not None
            else pd.DataFrame()
        )
        sales_vouchers = (
            generate_sales_vouchers(match_result)
            if match_result is not None
            else pd.DataFrame()
        )

        import pandas as pd
        vouchers_dir = config.data_dirs.get("vouchers", "../03_凭证输出")
        save_vouchers(bank_vouchers, invoice_vouchers, sales_vouchers, vouchers_dir)
        logging.info(f"凭证已保存至: {vouchers_dir}")

        pending_count = len(bank_classified[bank_classified["分类"].str.contains("待确认", na=False)])
        notifications = generate_notifications(match_result, pending_count)
        print_notifications(notifications)

        notif_dir = config.data_dirs.get("reports", "../04_税务报表")
        save_notifications(
            notifications,
            str(Path(notif_dir) / f"待处理事项_{year}年{month:02d}月.xlsx"),
        )

        logging.info("=== 全流程执行完成 ===")

    except Exception as e:
        logging.error(f"执行失败: {e}", exc_info=True)
        raise


def run_step(step: int, year: int, month: int):
    setup_logging()

    steps = {
        1: lambda: step1_process_bank_statements(year, month),
    }

    if step in steps:
        steps[step]()
    else:
        print(f"未知步骤: {step}，可选: 1-5, all")


def main():
    parser = argparse.ArgumentParser(description="AI财务自动化工作流")
    parser.add_argument("--step", type=str, default="all",
                        help="执行步骤: 1-5, all")
    parser.add_argument("--year", type=int, default=datetime.now().year,
                        help="年份")
    parser.add_argument("--month", type=int, default=datetime.now().month,
                        help="月份")
    parser.add_argument("--interactive", action="store_true",
                        help="交互模式，每步完成后暂停")

    args = parser.parse_args()

    if args.step == "all":
        run_all(args.year, args.month)
    else:
        try:
            step_num = int(args.step)
            run_step(step_num, args.year, args.month)
        except ValueError:
            print(f"无效步骤: {args.step}")


if __name__ == "__main__":
    main()
