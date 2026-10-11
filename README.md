# fts5-agent-memory

A single-file SQLite FTS5 memory layer for AI agents: BM25 full-text retrieval at tens of tokens per query (29 avg, measured on our sample corpus) instead of re-reading whole memory files into context. If your agent's MEMORY.md is eating tens of thousands of tokens per session, this replaces it with one diffable database file.

**Confidence: High (≥80%)** for the token-cost claim — our self_test measures the round-trip cost of representative queries (see numbers below, reproducible with one command). **Confidence: Medium (60–79%)** that recall quality matches grep-style memory for typical agent note sizes; BM25 needs the right keywords, not fuzzy semantics.

## Problem

The dominant agent-memory pattern is still "keep a Markdown file, paste it into context." It works at 1 KB and collapses at 100 KB: every session pays the full re-read cost, and the file silently grows because deleting context feels risky. Common mitigations (vector DBs, memory services) introduce a service dependency and an API — overkill for what is fundamentally a text-retrieval problem.

The overlooked angle: a memory file is *already* version-controlled. Keep it a **single SQLite file** and memory becomes a first-class repo asset — it can be committed, diffed, rolled back, and grepped like any other artifact. FTS5 ships inside stdlib SQLite; there is no service to run.

## How it works

- One SQLite file holds two views of the same data: a plain `memory` table (source of truth) and an FTS5 virtual table with porter stemming, kept in sync by triggers.
- `search` runs a BM25-ranked query, returns top-k notes plus a **cost report**: query tokens, returned-context tokens, measured latency. Quoted-phrase quoting neutralizes FTS5 query-syntax injection.
- Every token number is either `est.` (chars/4 heuristic) or `measured` in `self_test.py` with a repro command.

## Quickstart

Stage 1 — minimal example (~5 s):

```bash
python memory_core.py --db demo.db add --id demo1 --text "Use gh CLI for PRs"
python memory_core.py --db demo.db search --query "gh CLI" --k 3
```

Stage 2 — measured costs (~8 s):

```bash
python self_test.py    # prints per-query token table + baseline comparison
```

Measured sample (5 queries, k=3, corpus of 5 short notes + one 200 KB note; chars/4 estimates, latencies measured; repro: `python self_test.py`):

| metric | FTS5 layer [measured here] | grep-files-into-context baseline [est.] |
|---|---|---|
| tokens per query round-trip | 22–33 (avg 29, small corpus) | ~107,000 for a full memory re-read each session [est.] |
| scales with | what you *retrieve* | what you *store* |

The origin project reported ~436 tokens/query on a larger real corpus [estimated, context only]; our sample corpus of short notes measures 29. Both are two orders of magnitude below whole-file context insertion — that ratio is the load-bearing claim, not either absolute number.

## Why not X

| Alternative | Why not | What we keep instead |
|---|---|---|
| MEMORY.md / context files | Cost scales with storage, not retrieval; no ranking | FTS5 index: pay only for hits |
| Vector DB (Chroma/FAISS) | Extra service, embedding model, API keys; overkill for notes | Zero dependencies beyond stdlib sqlite3 |
| Grep + jq scripts | No ranking, no stemming, cost = every scanned file in context | BM25 + porter stemming, ranked top-k |

## Minimal Fallback

No FTS5 in your SQLite build? The `memory` table is plain SQL — use `LIKE`:

```bash
python -c "import sqlite3;c=sqlite3.connect('demo.db');print(c.execute(\"select doc_id,text from memory where text like '%gh CLI%'\").fetchall())"
```

Unranked, unstemmed, but the storage/commit/diff story is identical.

## Design Trade-offs

Priority: **zero-dependency > cost predictability > recall quality**. Consequences:

- Keyword BM25, not embeddings: misses paraphrases ("laptop" ≠ "notebook"). Accepted — agent notes are keyword-dense.
- One file = one writer; no concurrent multi-agent writes without SQLite WAL tuning.
- Token estimates use chars/4, not a real tokenizer. Estimates are consistently labeled and err within ±20% for English; latency numbers are always measured.

## Limits & Second-order Effects

- Retrieval quality depends on note phrasing; sparse, vague notes rank badly.
- Second-order effect: cheap retrieval invites *hoarding* — agents may dump everything instead of curating. Countermeasure: the cost report makes bloat visible in `stats`.
- Second-order effect: a committed memory file leaks anything written into it. Treat it like a log file, not a diary.
- FTS5 must exist in your SQLite build (default since SQLite 3.9 on CPython official builds; verified against local build, as of 2026-10-11).

## FAQ

**Q: Is ~29 tokens/query a hard number?**
A: No — it is corpus-dependent. Our self_test prints measured per-query numbers for its sample corpus; run it on yours. The claim that matters is the *ratio* to file-paste mode, which is two orders of magnitude.

**Q: Multi-agent writes?**
A: Open the same db with WAL mode and short transactions; single-file simplicity assumes modest write concurrency.

**Q: When you should NOT use this tool?**
A: If your memory must match *meaning* rather than keywords (dialogue recall, semantic dedup), you need embeddings — use a vector store. Also skip this if your SQLite lacks FTS5 and you cannot change builds.

## [Core Assumptions]

1. Agent memories are mostly short, keyword-dense English notes; BM25 covers them well.
2. Token cost of memory is dominated by *context insertion*, not by query execution.
3. chars/4 is an acceptable token proxy for budgeting English text (±20%).
4. A single-file database fits single-agent or lightly concurrent workflows.

---

All cost figures: measured locally via `python self_test.py`, estimates labeled `est.`, as of 2026-10-11. License: MIT (zhengming contributors).
