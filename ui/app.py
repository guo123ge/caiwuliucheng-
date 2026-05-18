import streamlit as st
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

st.set_page_config(page_title="AI财务自动化工作流", layout="wide")
st.title("💰 AI 财务自动化工作流系统")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 银行流水", "🧾 发票处理", "🔗 关联分析", "📋 凭证生成", "📈 税务报表"])

with tab1:
    st.header("流程1: 银行流水处理")
    col1, col2 = st.columns(2)
    with col1:
        year = st.number_input("年份", 2020, 2030, 2025, key="bank_year")
        month = st.number_input("月份", 1, 12, 5, key="bank_month")
    with col2:
        st.metric("数据目录", "00_原始数据/")
        st.metric("输出目录", "01_分类汇总/")
    
    if st.button("🚀 执行银行流水分类", type="primary"):
        with st.spinner("正在读取和分类..."):
            try:
                from data.data_merger import merge_bank_statements
                from ai.classifier import classify_dataframe, get_classification_summary
                from config import config
                
                raw_dir = config.data_dirs.get("raw_data", "../00_原始数据")
                merged = merge_bank_statements(raw_dir, year, month)
                classified = classify_dataframe(merged)
                summary = get_classification_summary(classified)
                
                st.success(f"✅ 处理完成！共 {len(merged)} 条记录")
                
                cache_hits = len(classified[classified["分类方法"] == "cache"])
                keyword_hits = len(classified[classified["分类方法"] == "keyword"])
                llm_calls = len(classified[classified["分类方法"] == "llm"])
                
                c1, c2, c3 = st.columns(3)
                c1.metric("缓存命中", cache_hits)
                c2.metric("关键词匹配", keyword_hits)
                c3.metric("LLM分类", llm_calls)
                
                st.subheader("分类汇总")
                st.dataframe(summary, use_container_width=True)
                
                st.subheader("分类明细（前20条）")
                display_cols = [c for c in ["交易日期", "摘要", "收入金额", "支出金额", "分类", "置信度", "分类方法"] if c in classified.columns]
                st.dataframe(classified[display_cols].head(20), use_container_width=True)
                
            except FileNotFoundError as e:
                st.warning(f"⚠ 未找到数据文件: {e}")
            except Exception as e:
                st.error(f"❌ 错误: {e}")

with tab2:
    st.header("流程2: 发票处理")
    st.info("📌 请先将发票明细Excel放入 00_原始数据/ 目录")
    col1, col2 = st.columns(2)
    with col1:
        inv_year = st.number_input("年份", 2020, 2030, 2025, key="inv_year")
        inv_month = st.number_input("月份", 1, 12, 5, key="inv_month")
    with col2:
        st.metric("发票分类", "抵减材料款 / 报销 / 借款 / 固定资产")
    
    if st.button("🚀 执行发票分类", type="primary"):
        st.info("请先执行银行流水处理，然后运行 main.py --step 2")

with tab3:
    st.header("流程2B: 账户-发票关联分析")
    st.info("📌 纯规则引擎（fuzzywuzzy模糊匹配），零LLM消耗")
    
    status_map = {
        "RECEIVED_MATCHED": "✅ 已收款+已开票",
        "PAID_MATCHED": "✅ 已付款+已收票",
        "RECEIVED_NEED_INVOICE": "📝 已收款，需开票",
        "PAYMENT_NO_INVOICE": "📋 已付款，需索票",
        "INVOICE_NO_PAYMENT": "📄 有票无流水",
        "RECEIVED_NO_INVOICE": "⚠ 已收款无发票",
    }
    
    st.subheader("关联状态说明")
    for status, desc in status_map.items():
        st.text(f"{desc} → {status}")

with tab4:
    st.header("流程3: 凭证生成")
    st.info("📌 模板填充生成，零LLM消耗")
    
    st.subheader("科目映射预览")
    from config import config
    mappings = config.category_subject_mapping
    rows = []
    for cat, info in mappings.items():
        rows.append({
            "分类": cat,
            "借方科目": info.get("debit", ""),
            "借方编码": info.get("debit_code", ""),
            "贷方科目": info.get("credit", ""),
            "贷方编码": info.get("credit_code", ""),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)

with tab5:
    st.header("流程4-5: 税务测算与财务报表")
    st.info("📌 纯公式计算，零LLM消耗")
    
    st.subheader("税率配置预览")
    tax_rules = config.tax_rules
    col1, col2 = st.columns(2)
    with col1:
        st.write("**增值税**")
        vat = tax_rules.get("value_added_tax", {})
        st.text(f"一般税率: {vat.get('general_tax_rate', 0)*100}%")
        st.text(f"低税率: {vat.get('low_tax_rate', 0)*100}%")
        
        st.write("**附加税**")
        surtax = tax_rules.get("surtax", {})
        st.text(f"城建税: {surtax.get('urban_construction', 0)*100}%")
        st.text(f"教育费附加: {surtax.get('education', 0)*100}%")
        st.text(f"地方教育附加: {surtax.get('local_education', 0)*100}%")
    with col2:
        st.write("**企业所得税**")
        cit = tax_rules.get("corporate_income_tax", {})
        st.text(f"标准税率: {cit.get('standard_rate', 0)*100}%")
        st.text(f"小微企业: {cit.get('small_micro_rate', 0)*100}%")
        
        st.write("**印花税**")
        stamp = tax_rules.get("stamp_duty", {})
        st.text(f"购销合同: {stamp.get('purchase_sale_contract', 0)*100}%")

st.sidebar.title("⚙️ 系统状态")
st.sidebar.success("✅ 系统就绪")

try:
    from ai.classification_cache import get_stats
    stats = get_stats()
    st.sidebar.metric("缓存条目", stats.get("total_entries", 0))
    st.sidebar.metric("累计命中", stats.get("total_hits", 0))
except:
    st.sidebar.metric("缓存条目", 0)

st.sidebar.subheader("LLM配置")
st.sidebar.text(f"Provider: {config.llm_provider}")
st.sidebar.text(f"Model: {config.deepseek_model}")
st.sidebar.text(f"批量上限: {config.llm_threshold.get('max_batch_size', 50)}条")
st.sidebar.text(f"置信度阈值: {config.llm_threshold.get('min_confidence', 0.7)}")

st.sidebar.subheader("API消耗预估")
st.sidebar.metric("预计月度LLM调用", "1-5次")
st.sidebar.metric("预计月度成本", "≈ ¥0.05")
