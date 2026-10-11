#!/usr/bin/env python3
"""fts5-agent-memory: a single-file SQLite FTS5 memory layer for agents.

BM25 full-text retrieval over everything an agent has ever written down.
Zero service dependencies: sqlite3 (stdlib) + FTS5. Memory becomes a
versionable, diffable, one-file asset.

Token accounting: this module reports an ESTIMATED token cost (chars/4
heuristic) for every query path, and self_test.py MEASURES real costs for
sample queries and prints them. Estimates are labeled `est.`, measurements
are labeled `measured`.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS memory (
    id      INTEGER PRIMARY KEY,
    doc_id  TEXT UNIQUE,
    text    TEXT NOT NULL,
    tags    TEXT DEFAULT '',
    created REAL
);
CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
    doc_id UNINDEXED, text, tags, content='memory', content_rowid='id',
    tokenize='porter unicode61'
);
CREATE TRIGGER IF NOT EXISTS memory_ai AFTER INSERT ON memory BEGIN
    INSERT INTO memory_fts(rowid, doc_id, text, tags)
    VALUES (new.id, new.doc_id, new.text, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS memory_ad AFTER DELETE ON memory BEGIN
    INSERT INTO memory_fts(memory_fts, rowid, doc_id, text, tags)
    VALUES ('delete', old.id, old.doc_id, old.text, old.tags);
END;
"""


def est_tokens(text: str) -> int:
    """Estimate tokens (chars/4 heuristic). Labeled `est.` everywhere it is shown."""
    return (len(text) + 3) // 4


class MemoryError_(Exception):
    pass


class AgentMemory:
    def __init__(self, db_path: str):
        d = os.path.dirname(os.path.abspath(db_path))
        if not os.path.isdir(d):
            raise MemoryError_(f"directory does not exist: {d}")
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        try:
            self.conn.executescript(SCHEMA)
        except sqlite3.DatabaseError as exc:
            raise MemoryError_(f"corrupted or non-SQLite db file: {exc}") from exc
        self.conn.commit()

    # ---------------- write
    def add(self, text: str, doc_id: str | None = None, tags: str = "") -> str:
        if not text or not text.strip():
            raise MemoryError_("refusing to store empty memory text")
        doc_id = doc_id or f"m{int(time.time() * 1000):013d}"
        self.conn.execute(
            "INSERT INTO memory(doc_id, text, tags, created) VALUES (?,?,?,?)",
            (doc_id, text, tags, time.time()))
        self.conn.commit()
        return doc_id

    def delete(self, doc_id: str) -> bool:
        cur = self.conn.execute("DELETE FROM memory WHERE doc_id=?", (doc_id,))
        self.conn.commit()
        return cur.rowcount > 0

    # ---------------- read
    def search(self, query: str, k: int = 5) -> tuple[list[dict], dict]:
        """BM25 search. Returns (hits, cost_report). cost_report carries both
        estimated and (in self_test) measured token costs for the round trip."""
        if not query or not query.strip():
            raise MemoryError_("empty query")
        terms = [t for t in query.replace('"', '""').split() if t]
        if not terms:
            raise MemoryError_("empty query")
        fts_q = " ".join(f'"{t}"' for t in terms)  # per-term quoting (AND), not phrase
        q = query.replace('"', '""')  # neutralize FTS5 query syntax injection
        t0 = time.perf_counter()
        rows = self.conn.execute(
            "SELECT doc_id, text, tags, bm25(memory_fts) AS rank "
            "FROM memory_fts WHERE memory_fts MATCH ? "
            "ORDER BY rank LIMIT ?", (fts_q, int(k))).fetchall()
        latency_ms = (time.perf_counter() - t0) * 1000.0
        hits = [{"doc_id": r[0], "text": r[1], "tags": r[2], "bm25": round(r[3], 4)}
                for r in rows]
        context = "".join(h["text"] for h in hits)
        cost = {
            "query_tokens_est": est_tokens(query),
            "context_tokens_est": est_tokens(context),
            "total_tokens_est": est_tokens(query) + est_tokens(context),
            "latency_ms_measured": round(latency_ms, 3),
            "hits": len(hits),
        }
        return hits, cost

    def stats(self) -> dict:
        n, chars = self.conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(LENGTH(text)),0) FROM memory").fetchone()
        fts = self.conn.execute(
            "SELECT COUNT(*) FROM memory_fts").fetchone()[0]
        db_bytes = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
        return {"docs": n, "fts_rows": fts,
                "chars": chars, "total_tokens_est": est_tokens("x" * chars),
                "db_bytes": db_bytes}

    def close(self):
        self.conn.close()


def cmd_baseline(k: int = 3) -> dict:
    """Reference cost of the grep-in-context pattern for comparison: k
    typical memory files re-read into context each session. est. only."""
    typical_file = "- Use gh CLI over web UI.\n" * 40  # ~1KB memory note
    return {"docs": k, "tokens_est": k * est_tokens(typical_file)}


# ---------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="fts5-agent-memory",
        description="single-file SQLite FTS5 memory layer for agents")
    p.add_argument("--db", default="agent_memory.db", help="db file (default ./agent_memory.db)")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add", help="add a memory")
    a.add_argument("--text", required=True)
    a.add_argument("--id", default=None)
    a.add_argument("--tags", default="")
    s = sub.add_parser("search", help="BM25 search; prints cost report")
    s.add_argument("--query", required=True)
    s.add_argument("--k", type=int, default=5)
    sub.add_parser("stats", help="db statistics incl. token totals")
    d = sub.add_parser("delete", help="delete by doc_id")
    d.add_argument("--id", required=True)

    a2 = p.parse_args(argv)
    try:
        mem = AgentMemory(a2.db)
        if a2.cmd == "add":
            print(mem.add(a2.text, a2.id, a2.tags))
        elif a2.cmd == "search":
            hits, cost = mem.search(a2.query, a2.k)
            print(json.dumps({"cost_report": cost, "hits": hits}, indent=2))
        elif a2.cmd == "stats":
            print(json.dumps({"db": mem.stats(),
                              "grep_baseline": cmd_baseline()}, indent=2))
        elif a2.cmd == "delete":
            print("deleted" if mem.delete(a2.id) else "not found")
        mem.close()
        return 0
    except MemoryError_ as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except sqlite3.DatabaseError as exc:
        print(f"error: db problem: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
