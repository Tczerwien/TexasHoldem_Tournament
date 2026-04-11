---
phase: 2
slug: preflop-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-11
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Python unittest + engine simulation |
| **Config file** | none |
| **Quick run command** | `python -c "import players.mtt_bot"` |
| **Full suite command** | `cd Docs/MTT-Pokerbot-Engine && python main.py` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -c "import players.mtt_bot"` (syntax check)
- **After every plan wave:** Run existing test suites + new preflop tests
- **Before `/gsd-verify-work`:** Full 10-sim run must complete
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 1 | COMP-01 | — | N/A | unit | `python -c "from players.mtt_bot import FULL_DECK; assert len(FULL_DECK)==52"` | ❌ W0 | ⬜ pending |
| 2-01-02 | 01 | 1 | COMP-02 | — | N/A | unit | `python -c "from players.mtt_bot import CHEN_TABLE; assert len(CHEN_TABLE)==169"` | ❌ W0 | ⬜ pending |
| 2-01-03 | 01 | 1 | COMP-03 | — | N/A | unit | `python -c "from players.mtt_bot import SHOVE_TABLE; assert len(SHOVE_TABLE)==169"` | ❌ W0 | ⬜ pending |
| 2-01-04 | 01 | 1 | COMP-04 | — | N/A | unit | `python -c "from players.mtt_bot import CALL_TABLE; assert len(CALL_TABLE)==169"` | ❌ W0 | ⬜ pending |
| 2-01-05 | 01 | 1 | PRE-01 | — | N/A | unit | Chen formula test | ❌ W0 | ⬜ pending |
| 2-02-01 | 02 | 2 | PRE-02 | — | N/A | integration | Stack mode detection test | ❌ W0 | ⬜ pending |
| 2-02-02 | 02 | 2 | PRE-03 | — | N/A | integration | Opening range width test | ❌ W0 | ⬜ pending |
| 2-02-03 | 02 | 2 | PRE-04 | — | N/A | integration | Push-fold shove test | ❌ W0 | ⬜ pending |
| 2-02-04 | 02 | 2 | PRE-05 | — | N/A | integration | Push-fold call test | ❌ W0 | ⬜ pending |
| 2-02-05 | 02 | 2 | PRE-06 | — | N/A | integration | Situation detection test | ❌ W0 | ⬜ pending |
| 2-02-06 | 02 | 2 | PRE-07 | — | N/A | integration | Situational strategy test | ❌ W0 | ⬜ pending |
| 2-02-07 | 02 | 2 | PRE-08 | — | N/A | integration | 3-bet/4-bet logic test | ❌ W0 | ⬜ pending |
| 2-02-08 | 02 | 2 | PRE-09 | — | N/A | integration | Raise sizing test | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_preflop.py` — preflop engine test suite

*No framework to install — Python unittest is built-in.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Range widths approximate correctness | PRE-03 | Approximate percentages require counting over full deck | Run simulation, check bot doesn't open too wide or too tight |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
