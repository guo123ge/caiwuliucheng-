import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional


BACKUP_DIR_NAME = "_backups"


def backup_file(file_path: str, backup_root: Optional[str] = None) -> Optional[str]:
    src = Path(file_path)
    if not src.exists():
        return None

    if backup_root is None:
        backup_root = str(src.parent / BACKUP_DIR_NAME)
    else:
        backup_root = str(Path(backup_root) / BACKUP_DIR_NAME)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(backup_root) / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)

    dst = backup_dir / src.name
    shutil.copy2(src, dst)
    return str(dst)


def backup_directory(dir_path: str, backup_root: Optional[str] = None) -> Optional[str]:
    src = Path(dir_path)
    if not src.exists() or not src.is_dir():
        return None

    if backup_root is None:
        backup_root = str(src.parent / BACKUP_DIR_NAME)
    else:
        backup_root = str(Path(backup_root) / BACKUP_DIR_NAME)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(backup_root) / f"{src.name}_{timestamp}"

    shutil.copytree(src, backup_dir)
    return str(backup_dir)


def backup_data_dirs(data_dirs: dict) -> List[str]:
    backups = []
    for key, dir_path in data_dirs.items():
        if key == "raw_data":
            continue
        result = backup_directory(dir_path)
        if result:
            backups.append(result)
    return backups


def cleanup_old_backups(backup_root: str, keep_days: int = 30):
    root = Path(backup_root)
    if not root.exists():
        return

    cutoff = time.time() - keep_days * 86400
    for item in root.iterdir():
        if item.is_dir():
            try:
                mtime = item.stat().st_mtime
                if mtime < cutoff:
                    shutil.rmtree(item)
            except Exception:
                pass
