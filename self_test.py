#!/usr/bin/env python3
"""self_test for fts5-agent-memory — MEASURES per-query token costs.

Three test classes (rule 97) + a measured cost report.
Run:  python self_test.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import memory_core as m  # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))


# realistic memory corpus (~50 notes like a real agent would write)
CORPUS = [
    ("deploy-gh", "Always use gh CLI for PR operations instead of the web UI; "
                  "web actions bypass hook checks.", "workflow"),
    ("ctx-ledger", "Externalize big tool outputs into SQLite FTS5; keep only a "
                   "pointer in context to stay under the token budget.", "memory"),
    ("tts-stack", "edge-tts synthesizes audiobooks for free; batch chapter files "
                  "then concatenate with ffmpeg.", "media"),
    ("pricing-rule", "Never quote prices from memory; fetch current page and mark "
                     "the date (as-of discipline).", "finance"),
    ("pentest-ethics", "Only scan assets the user owns; dual-graph lab analysis "
                       "requires explicit authorization flag.", "safety"),
]


def main() -> int:
    td = tempfile.mkdtemp()
    db = os.path.join(td, "mem.db")
    mem = m.AgentMemory(db)
    for did, text, tag in CORPUS:
        mem.add(text, doc_id=did, tags=tag)

    # ---------------- A. functional
    hits, cost = mem.search("PR operations gh CLI", k=3)
    check("A1 BM25 ranks exact-match note first",
          hits and hits[0]["doc_id"] == "deploy-gh", f"got {hits[:1]}")
    check("A2 cost report has est fields",
          all(f in cost for f in ("query_tokens_est", "context_tokens_est",
                                  "total_tokens_est", "latency_ms_measured")))
    check("A3 cost total == query + context (est)",
          cost["total_tokens_est"] == cost["query_tokens_est"] + cost["context_tokens_est"])
    st = mem.stats()
    check("A4 stats counts 5 docs", st["docs"] == 5, str(st))
    check("A5 fts rows mirror docs", st["fts_rows"] == 5)
    did = mem.add("temp note to delete", doc_id="tmp1")
    check("A6 add returns doc_id", did == "tmp1")
    check("A7 delete removes it", mem.delete("tmp1") is True)

    # ---------------- B. error paths
    try:
        mem.search("")
        check("B1 empty query raises", False)
    except m.MemoryError_:
        check("B1 empty query raises", True)
    try:
        mem.add("   ")
        check("B2 empty text rejected", False)
    except m.MemoryError_:
        check("B2 empty text rejected", True)
    try:
        m.AgentMemory(os.path.join(td, "no_such_dir", "x.db"))
        check("B3 missing dir raises", False)
    except m.MemoryError_:
        check("B3 missing dir raises", True)
    dup = os.path.join(td, "dup.db")
    mem2 = m.AgentMemory(dup)
    mem2.add("x", doc_id="dup1")
    try:
        mem2.add("y", doc_id="dup1")
        check("B4 duplicate doc_id raises sqlite IntegrityError path", False)
    except Exception:
        check("B4 duplicate doc_id raises sqlite IntegrityError path", True)
    bad = os.path.join(td, "corrupt.db")
    with open(bad, "wb") as f:
        f.write(b"this is not a sqlite file at all, just bytes")
    try:
        m.AgentMemory(bad)
        check("B5 corrupted db file rejected with clear error", False)
    except m.MemoryError_:
        check("B5 corrupted db file rejected with clear error", True)

    # ---------------- C. extreme edges
    hits, _ = mem.search("zzz-no-such-term-anywhere", k=5)
    check("C1 zero-hit query returns empty list", hits == [])
    huge = ("long memory line about fts5 and bm25 and agents. " * 4000)  # ~200KB
    mem.add(huge, doc_id="huge1")
    hits, cost = mem.search("fts5 and bm25", k=5)
    check("C2 200KB doc indexed and retrievable",
          any(h["doc_id"] == "huge1" for h in hits), str(cost))
    check("C3 context cost est scales with hit length",
          cost["context_tokens_est"] > 20_000)
    check("C4 FTS5 syntax injection is neutralized",
          mem.search('body" OR 1=1 --') is not None)
    long_query = "memory " * 5000  # ~35KB query
    hits, cost = mem.search(long_query, k=1)
    check("C5 35KB query survives", isinstance(hits, list))

    # ---------------- MEASURED COST REPORT (the deliverable claim)
    print("\n=== measured per-query token cost (chars/4 estimate of round-trip "
          "context: query text + returned hit texts) ===")
    queries = ["PR operations gh CLI", "token budget context", "edge-tts audiobook",
               "authorization flag dual-graph", "as-of discipline pricing"]
    tot = 0
    for q in queries:
        hits, c = mem.search(q, k=3)
        tot += c["total_tokens_est"]
        print(f"  query={q[:30]!r:34} hits={c['hits']}  "
              f"query_tok={c['query_tokens_est']:>4}  "
              f"ctx_tok={c['context_tokens_est']:>5}  "
              f"total={c['total_tokens_est']:>5} tok  "
              f"latency={c['latency_ms_measured']:>7.2f} ms")
    st = mem.stats()
    print(f"\n  avg tokens/query (measured over {len(queries)} queries): {tot//len(queries)}")
    print(f"  whole-memory context cost: {st['total_tokens_est']} tok est. "
          f"({st['docs']} docs, {st['db_bytes']} bytes)")
    print(f"  grep-into-context baseline (3 files x ~1KB, est.): "
          f"{m.cmd_baseline()['tokens_est']} tok")
    print("  NOTE: token numbers are chars/4 estimates (est.), latencies are "
          "measured; repro: python self_test.py")

    mem.close()
    fails = [r for r in RESULTS if not r[1]]
    print("\n" + "=" * 60)
    for name, ok, detail in RESULTS:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))
    print(f"\ntotal={len(RESULTS)} pass={len(RESULTS)-len(fails)} fail={len(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
