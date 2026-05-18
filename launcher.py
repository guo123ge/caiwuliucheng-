import os
import subprocess
import sys
import webbrowser
import time
from pathlib import Path


def main():
    app_dir = Path(__file__).parent.resolve()
    ui_path = app_dir / "ui" / "app.py"

    if not ui_path.exists():
        print(f"错误: 找不到 {ui_path}")
        input("按 Enter 退出...")
        sys.exit(1)

    streamlit_cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(ui_path),
        "--server.port", "8501",
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--server.maxUploadSize", "50",
    ]

    print("=" * 50)
    print("  AI 财务自动化工作流 v1.0")
    print("=" * 50)
    print("正在启动服务...")

    try:
        proc = subprocess.Popen(
            streamlit_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        time.sleep(3)
        webbrowser.open("http://localhost:8501")

        print("服务已启动: http://localhost:8501")
        print("浏览器应已自动打开，如未打开请手动访问上述地址")
        print("按 Ctrl+C 或关闭此窗口停止服务")
        print("=" * 50)

        for line in proc.stdout:
            print(line, end="")

    except KeyboardInterrupt:
        print("\n正在停止服务...")
        proc.terminate()
        proc.wait()
        print("服务已停止")
    except Exception as e:
        print(f"启动失败: {e}")
        input("按 Enter 退出...")


if __name__ == "__main__":
    main()
