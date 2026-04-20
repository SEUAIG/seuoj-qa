"""
轻量级 SQLite 数据库模块

替代 Django ORM，使用 Python 标准库 sqlite3 直接操作数据库。
零额外依赖，开箱即用。

表结构：
- chat_session: 聊天会话
- chat_message: 聊天消息
- citation: 引用来源
- message_citation: 消息-引用关联
"""

import sqlite3
import uuid
import threading
from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager
from typing import Optional, List

# 默认数据库路径
DB_PATH = Path(__file__).parent / "data" / "chat.db"


def generate_id() -> str:
    """生成32位无横杠UUID"""
    return uuid.uuid4().hex


# ============================================================
# 连接管理（线程安全）
# ============================================================

_local = threading.local()


def get_connection(db_path: Path = None) -> sqlite3.Connection:
    """获取当前线程的数据库连接（复用）"""
    path = str(db_path or DB_PATH)
    if not hasattr(_local, "connections"):
        _local.connections = {}
    if path not in _local.connections:
        conn = sqlite3.connect(path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.connections[path] = conn
    return _local.connections[path]


@contextmanager
def get_db(db_path: Path = None):
    """上下文管理器，自动 commit/rollback"""
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


# ============================================================
# 建表
# ============================================================

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS chat_session (
    session_id  TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    title       TEXT NOT NULL,
    last_message TEXT,
    course_id   TEXT,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_session_user_id ON chat_session(user_id);
CREATE INDEX IF NOT EXISTS idx_session_course_id ON chat_session(course_id);
CREATE INDEX IF NOT EXISTS idx_session_updated_at ON chat_session(updated_at DESC);

CREATE TABLE IF NOT EXISTS citation (
    citation_id  TEXT PRIMARY KEY,
    source_type  TEXT NOT NULL,
    source_title TEXT NOT NULL,
    location     TEXT,
    snippet      TEXT,
    document_id  TEXT,
    chunk_id     TEXT,
    created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now'))
);

CREATE TABLE IF NOT EXISTS chat_message (
    id                TEXT PRIMARY KEY,
    session_id        TEXT NOT NULL REFERENCES chat_session(session_id) ON DELETE CASCADE,
    role              TEXT NOT NULL,
    content           TEXT NOT NULL,
    parent_message_id TEXT REFERENCES chat_message(id) ON DELETE SET NULL,
    timestamp         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_message_session_ts ON chat_message(session_id, timestamp);

CREATE TABLE IF NOT EXISTS message_citation (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id      TEXT NOT NULL REFERENCES chat_message(id) ON DELETE CASCADE,
    citation_id     TEXT NOT NULL REFERENCES citation(citation_id) ON DELETE CASCADE,
    citation_number INTEGER NOT NULL,
    UNIQUE(message_id, citation_number)
);

CREATE INDEX IF NOT EXISTS idx_mc_message_id ON message_citation(message_id);
"""


def init_db(db_path: Path = None):
    """初始化数据库（建表）"""
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(path)
    conn.executescript(SCHEMA_SQL)
    conn.commit()


# ============================================================
# CRUD 操作
# ============================================================

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")


def _row_to_dict(row) -> dict:
    if row is None:
        return None
    return dict(row)


# ---------- ChatSession ----------

def create_session(user_id: str, title: str, course_id: str = None) -> dict:
    """创建新会话"""
    session_id = generate_id()
    now = _now()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO chat_session (session_id, user_id, title, course_id, created_at, updated_at) VALUES (?,?,?,?,?,?)",
            (session_id, user_id, title, course_id, now, now)
        )
    return {
        "session_id": session_id,
        "user_id": user_id,
        "title": title,
        "course_id": course_id,
        "last_message": None,
        "created_at": now,
        "updated_at": now,
    }


def get_session(session_id: str) -> Optional[dict]:
    """获取单个会话"""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM chat_session WHERE session_id=?", (session_id,)
    ).fetchone()
    return _row_to_dict(row)


def list_sessions(user_id: str, course_id: str = None) -> List[dict]:
    """列出用户会话"""
    conn = get_connection()
    if course_id:
        rows = conn.execute(
            "SELECT * FROM chat_session WHERE user_id=? AND course_id=? ORDER BY updated_at DESC",
            (user_id, course_id)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM chat_session WHERE user_id=? ORDER BY updated_at DESC",
            (user_id,)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def update_session(session_id: str, **kwargs) -> Optional[dict]:
    """更新会话字段（title, last_message 等）"""
    allowed = {"title", "last_message", "course_id"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return get_session(session_id)
    fields["updated_at"] = _now()
    set_clause = ", ".join(f"{k}=?" for k in fields)
    values = list(fields.values()) + [session_id]
    with get_db() as conn:
        conn.execute(
            f"UPDATE chat_session SET {set_clause} WHERE session_id=?", values
        )
    return get_session(session_id)


def delete_session(session_id: str) -> bool:
    """删除会话（级联删除消息和关联）"""
    with get_db() as conn:
        cur = conn.execute("DELETE FROM chat_session WHERE session_id=?", (session_id,))
    return cur.rowcount > 0


# ---------- ChatMessage ----------

def create_message(session_id: str, role: str, content: str,
                   parent_message_id: str = None) -> dict:
    """创建消息"""
    msg_id = generate_id()
    now = _now()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO chat_message (id, session_id, role, content, parent_message_id, timestamp) VALUES (?,?,?,?,?,?)",
            (msg_id, session_id, role, content, parent_message_id, now)
        )
        # 更新会话的 last_message 和 updated_at
        conn.execute(
            "UPDATE chat_session SET last_message=?, updated_at=? WHERE session_id=?",
            (content[:100], now, session_id)
        )
    return {
        "id": msg_id,
        "session_id": session_id,
        "role": role,
        "content": content,
        "parent_message_id": parent_message_id,
        "timestamp": now,
        "citations": [],
    }


def get_messages(session_id: str) -> List[dict]:
    """获取会话的所有消息（含引用）"""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM chat_message WHERE session_id=? ORDER BY timestamp",
        (session_id,)
    ).fetchall()

    messages = []
    for row in rows:
        msg = _row_to_dict(row)
        # 加载引用
        cit_rows = conn.execute("""
            SELECT mc.citation_number, c.*
            FROM message_citation mc
            JOIN citation c ON mc.citation_id = c.citation_id
            WHERE mc.message_id=?
            ORDER BY mc.citation_number
        """, (msg["id"],)).fetchall()
        msg["citations"] = [
            {"citation_number": r["citation_number"], **{k: r[k] for k in
             ["citation_id", "source_type", "source_title", "location", "snippet", "document_id", "chunk_id"]}}
            for r in cit_rows
        ]
        messages.append(msg)
    return messages


# ---------- Citation ----------

def create_citation(source_type: str, source_title: str,
                    location: str = None, snippet: str = None,
                    document_id: str = None, chunk_id: str = None) -> dict:
    """创建引用"""
    cit_id = generate_id()
    now = _now()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO citation (citation_id, source_type, source_title, location, snippet, document_id, chunk_id, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (cit_id, source_type, source_title, location, snippet, document_id, chunk_id, now)
        )
    return {
        "citation_id": cit_id,
        "source_type": source_type,
        "source_title": source_title,
        "location": location,
        "snippet": snippet,
        "document_id": document_id,
        "chunk_id": chunk_id,
        "created_at": now,
    }


def link_citation(message_id: str, citation_id: str, citation_number: int):
    """关联消息和引用"""
    with get_db() as conn:
        conn.execute(
            "INSERT INTO message_citation (message_id, citation_id, citation_number) VALUES (?,?,?)",
            (message_id, citation_id, citation_number)
        )


# ---------- 组合操作 ----------

def create_assistant_message_with_citations(
    session_id: str, content: str, citations: list = None,
    parent_message_id: str = None
) -> dict:
    """
    创建 AI 回复（包含引用），事务内完成

    citations 格式: list[dict] 或 list[str]
    """
    msg_id = generate_id()
    now = _now()
    result_citations = []

    with get_db() as conn:
        conn.execute(
            "INSERT INTO chat_message (id, session_id, role, content, parent_message_id, timestamp) VALUES (?,?,?,?,?,?)",
            (msg_id, session_id, "ASSISTANT", content, parent_message_id, now)
        )

        if citations:
            for idx, cit_data in enumerate(citations, 1):
                cit_id = generate_id()
                if isinstance(cit_data, str):
                    parts = cit_data.split("-", 1)
                    title = parts[0].strip() if parts else "参考资料"
                    location = parts[1].strip() if len(parts) > 1 else ""
                    source_type = "TEXTBOOK"
                    snippet = cit_data
                    document_id = None
                    chunk_id = None
                else:
                    source_type = cit_data.get("source_type", "OTHER")
                    title = cit_data.get("source_title", "")
                    location = cit_data.get("location")
                    snippet = cit_data.get("snippet")
                    document_id = cit_data.get("document_id")
                    chunk_id = cit_data.get("chunk_id")

                conn.execute(
                    "INSERT INTO citation (citation_id, source_type, source_title, location, snippet, document_id, chunk_id, created_at) VALUES (?,?,?,?,?,?,?,?)",
                    (cit_id, source_type, title, location, snippet, document_id, chunk_id, now)
                )
                conn.execute(
                    "INSERT INTO message_citation (message_id, citation_id, citation_number) VALUES (?,?,?)",
                    (msg_id, cit_id, idx)
                )
                result_citations.append({
                    "citation_number": idx,
                    "citation_id": cit_id,
                    "source_type": source_type,
                    "source_title": title,
                    "location": location,
                    "snippet": snippet,
                })

        conn.execute(
            "UPDATE chat_session SET last_message=?, updated_at=? WHERE session_id=?",
            (content[:100], now, session_id)
        )

    return {
        "id": msg_id,
        "session_id": session_id,
        "role": "ASSISTANT",
        "content": content,
        "parent_message_id": parent_message_id,
        "timestamp": now,
        "citations": result_citations,
    }
