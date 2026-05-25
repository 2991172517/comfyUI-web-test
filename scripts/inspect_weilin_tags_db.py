#!/usr/bin/env python3
"""查看 WeiLin tags SQLite 表结构与数量。"""
import sqlite3
import sys
from pathlib import Path

db = Path(
    sys.argv[1]
    if len(sys.argv) > 1
    else r"..\..\custom_nodes\WeiLin-Comfyui-Tools\user_data\userdatas_zh_CN_tags.db"
).resolve()
if not db.is_file():
    print("DB not found:", db)
    raise SystemExit(1)

c = sqlite3.connect(db)
tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("DB:", db)
for t in tables:
    n = c.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
    cols = [r[1] for r in c.execute(f"PRAGMA table_info([{t}])").fetchall()]
    print(f"  {t}: {n} rows — {cols}")
c.close()
