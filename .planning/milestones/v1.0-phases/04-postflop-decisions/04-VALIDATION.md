---
phase: 4
slug: postflop-decisions
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-11
---

# Phase 4 — Validation Strategy

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
| 4-01-01 | 01 | 1 | POST-06,07,08,09,10,11,12,13 | integration | ⬜ pending |

---

## Wave 0 Requirements

- [ ] `tests/test_postflop_decisions.py` — postflop decision test suite

---

## Validation Sign-Off

- [ ] All tasks have automated verify
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
