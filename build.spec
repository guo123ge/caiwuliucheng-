# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

project_root = Path(SPECPATH).parent

datas = [
    (str(project_root / "config" / "accounts.json"), "config"),
    (str(project_root / "config" / "categories.json"), "config"),
    (str(project_root / "config" / "subject_mapping.json"), "config"),
    (str(project_root / "config" / "tax_rules.json"), "config"),
    (str(project_root / "ui" / "app.py"), "ui"),
]

hidden_imports = [
    "streamlit",
    "streamlit.runtime",
    "streamlit.web",
    "streamlit.web.bootstrap",
    "streamlit.watcher",
    "pandas",
    "openpyxl",
    "fuzzywuzzy",
    "Levenshtein",
    "dotenv",
    "ai.classifier",
    "ai.classification_cache",
    "ai.invoice_classifier",
    "ai.llm_client",
    "data.excel_reader",
    "data.excel_writer",
    "data.data_merger",
    "data.data_validator",
    "data.account_matcher",
    "data.backup",
    "calculations.tax_calculator",
    "calculations.profit_calculator",
    "calculations.statement_generator",
    "vouchers.subject_mapping",
    "vouchers.voucher_generator",
    "output.summary_writer",
    "output.report_writer",
    "output.notification",
    "browser.browser_utils",
    "browser.jdy_client",
    "browser.login_manager",
    "config",
    "altair",
    "pyarrow",
    "numpy",
    "git",
    "watchdog",
]

a = Analysis(
    [str(project_root / "launcher.py")],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "scipy",
        "PIL",
        "cv2",
        "tensorflow",
        "torch",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="AI财务自动化工作流",
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
    icon=None,
)
