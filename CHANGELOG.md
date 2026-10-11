# Changelog

## v0.1.1 (2026-10-11) — self-review revision (iteration 2)

- **Correctness**: README no longer presents "436 tokens/query" as a universal figure — it is a corpus-dependent sample, now stated explicitly; the load-bearing claim (orders-of-magnitude ratio vs file-paste) is separated from the sample number.
- **Completeness (+~25%)**: added Minimal Fallback (LIKE-mode path for SQLite builds without FTS5), Limits entry on FTS5 build availability, and second-order effects (memory hoarding; committed memory as leak surface).
- **Correctness (code)**: self_test now measures and prints a 5-query token table + baseline, with est./measured discipline labels; added injection-neutralization test (C4) and corrupted-db test (B5).

## v0.1.0 (2026-10-11) — initial draft

- Single-file SQLite FTS5 memory: add/delete/search(BM25)/stats CLI.
- Per-query cost report (est. tokens + measured latency).
- self_test with functional / error-path / edge classes (17 checks).
