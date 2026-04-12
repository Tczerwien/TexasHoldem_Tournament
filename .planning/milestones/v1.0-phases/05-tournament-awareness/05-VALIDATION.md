---
phase: 5
slug: tournament-awareness
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-11
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Python pytest |
| **Quick run command** | `python -c "import players.mtt_bot"` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** `python -c "import players.mtt_bot"`
- **After every plan wave:** `python -m pytest tests/ -x -q`
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Status |
|---------|------|------|-------------|-----------|--------|
| 5-01-01 | 01 | 1 | TOURN-01,02,03,04,05,06,07 | unit/integration | ⬜ pending |

---

## Wave 0 Requirements

- [ ] `tests/test_tournament.py` — tournament awareness test suite

---

## Validation Sign-Off

- [ ] All tasks have automated verify
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
