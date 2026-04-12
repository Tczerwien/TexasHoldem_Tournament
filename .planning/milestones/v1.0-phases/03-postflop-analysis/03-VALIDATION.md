---
phase: 3
slug: postflop-analysis
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-11
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Python pytest |
| **Config file** | none |
| **Quick run command** | `python -c "import players.mtt_bot"` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** `python -c "import players.mtt_bot"` (syntax)
- **After every plan wave:** `python -m pytest tests/ -x -q` (full suite)
- **Before `/gsd-verify-work`:** Full suite green + engine simulation
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 3-01-01 | 01 | 1 | POST-01 | unit | `python -m pytest tests/test_postflop.py -x -q` | ⬜ pending |
| 3-01-02 | 01 | 1 | POST-02 | unit | `python -m pytest tests/test_postflop.py -x -q` | ⬜ pending |
| 3-02-01 | 02 | 2 | POST-03 | unit | `python -m pytest tests/test_postflop.py -x -q` | ⬜ pending |
| 3-02-02 | 02 | 2 | POST-04 | unit | `python -m pytest tests/test_postflop.py -x -q` | ⬜ pending |
| 3-02-03 | 02 | 2 | POST-05 | unit | `python -m pytest tests/test_postflop.py -x -q` | ⬜ pending |

---

## Wave 0 Requirements

- [ ] `tests/test_postflop.py` — postflop analysis test suite

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| MC equity plausibility | POST-02 | Statistical output varies by run | Verify AA equity ~0.85, 72o ~0.35 within tolerance |

---

## Validation Sign-Off

- [ ] All tasks have automated verify
- [ ] Sampling continuity maintained
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
