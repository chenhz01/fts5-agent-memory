# Alignment Audit (Rules 85-100 / 16 items)

Repo: fts5-agent-memory · Audited: 2026-10-11 · v0.1.1

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 1 | Safety/Ethics section | N/A | Non-security-domain tool. |
| 2 | Privacy/zero secrets | PASS | No keys/tokens/real names/emails; sample notes are generic practice notes. |
| 3 | Copyright boundary | PASS | No copied source text (>50 chars); origin concept re-described; MIT LICENSE present. |
| 4 | Fact-source labeling | PASS | All token figures est.-labeled or measured with repro `python self_test.py`; baseline marked [est.]. |
| 5 | Confidence grading | PASS | Top claim High (reproducible measurement); recall-quality claim Medium with reason. |
| 6 | Minimal Fallback | PASS | LIKE-mode fallback for FTS5-less builds. |
| 7 | Quickstart timing | PASS | Stage timings (~5 s / ~8 s) with staged path. |
| 8 | Design trade-offs/priorities | PASS | zero-dependency > cost predictability > recall quality, with consequences. |
| 9 | CHANGELOG ≥2 iterations | PASS | v0.1.0 → v0.1.1, deltas named. |
| 10 | Exemption (session rule) | N/A | Session-level; static repo. |
| 11 | Time-sensitive data dated | PASS | FTS5 build-availability note + footer "as of 2026-10-11". |
| 12 | Core assumptions ≥3 | PASS | 4 assumptions at README end. |
| 13 | Three-class self-test | PASS | A functional (7), B error paths (5), C edges (5); all PASS locally; cost table printed. Repro: `python self_test.py`. |
| 14 | When NOT to use | PASS | FAQ Q3: semantic matching / no FTS5. |
| 15 | ≥2 iterations traceable | PASS | v0.1.1 correctness + completeness deltas (≥20% on README honesty of figures). |
| 16 | ≤60-word first screen | PASS | First paragraph 58 words with a "this replaces it" judgment. |
