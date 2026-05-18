# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=[('config/accounts.json', 'config'), ('config/categories.json', 'config'), ('config/subject_mapping.json', 'config'), ('config/tax_rules.json', 'config'), ('ui/app.py', 'ui')],
    hiddenimports=['streamlit', 'pandas', 'openpyxl', 'fuzzywuzzy', 'Levenshtein', 'dotenv', 'altair', 'pyarrow', 'numpy', 'watchdog', 'ai.classifier', 'ai.classification_cache', 'ai.invoice_classifier', 'ai.llm_client', 'data.excel_reader', 'data.excel_writer', 'data.data_merger', 'data.data_validator', 'data.account_matcher', 'calculations.tax_calculator', 'calculations.profit_calculator', 'calculations.statement_generator', 'vouchers.subject_mapping', 'vouchers.voucher_generator', 'output.summary_writer', 'output.report_writer', 'output.notification', 'config'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AI-Finance-Workflow',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
