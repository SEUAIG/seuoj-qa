#!/usr/bin/env python
"""
数据库初始化脚本

使用方式:
    python init_db.py

功能:
    1. 在 src/data/ 下创建 SQLite 数据库文件 chat.db
    2. 创建所有业务表和索引
    3. 验证表创建成功
"""

import sys
from pathlib import Path

# 确保可以导入 database 模块
sys.path.insert(0, str(Path(__file__).parent))

from database import init_db, get_connection, resolve_db_path, DB_PATH_ENV_VAR


def main():
    db_path = resolve_db_path()

    print("=" * 50)
    print("  AIgorithm_Agent 数据库初始化 (SQLite)")
    print("=" * 50)
    print()

    # 1. 初始化（建表）
    print(f"[1/2] 初始化数据库: {db_path}")
    print(f"      路径来源: 环境变量 {DB_PATH_ENV_VAR} 或默认路径")
    init_db()
    print("      完成!")
    print()

    # 2. 验证
    print("[2/2] 验证数据表:")
    conn = get_connection()
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()

    expected = {"chat_session", "chat_message", "citation", "message_citation"}
    for row in rows:
        name = row["name"]
        mark = "ok" if name in expected else "  "
        print(f"      [{mark}] {name}")

    missing = expected - {r["name"] for r in rows}
    if missing:
        print(f"\n      [!] 缺少表: {missing}")
        sys.exit(1)

    print()
    print("=" * 50)
    print(f"  初始化完成! 数据库文件: {db_path}")
    print("=" * 50)


if __name__ == "__main__":
    main()
