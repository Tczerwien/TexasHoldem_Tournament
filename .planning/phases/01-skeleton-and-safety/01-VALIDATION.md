---
phase: 1
slug: skeleton-and-safety
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-10
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Engine simulation (run main.py with bot loaded) |
| **Config file** | Docs/MTT-Pokerbot-Engine/engine/config.py |
| **Quick run command** | `cd Docs/MTT-Pokerbot-Engine && python main.py` |
| **Full suite command** | `cd Docs/MTT-Pokerbot-Engine && python main.py` (10 simulations) |
| **Estimated runtime** | ~30-60 seconds per simulation |

---

## Sampling Rate

- **After every task commit:** Verify file syntax with `python -c "import players.mtt_bot"`
- **After every plan wave:** Run full simulation via engine
- **Before `/gsd-verify-work`:** Full 10-sim run must complete with zero crashes
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | SAFE-01 | — | N/A | integration | `python -c "from players.mtt_bot import HawkEyeBot"` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | SAFE-08 | — | N/A | integration | `python -c "import players.mtt_bot"` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | SAFE-09 | — | N/A | integration | `ls players/mtt_bot.py` | ❌ W0 | ⬜ pending |
| 1-01-04 | 01 | 1 | SAFE-02 | — | try/except wraps _decide | integration | `grep -c "except.*Exception" players/mtt_bot.py` | ❌ W0 | ⬜ pending |
| 1-01-05 | 01 | 1 | SAFE-03 | — | Never fold when free | integration | Engine simulation | ❌ W0 | ⬜ pending |
| 1-01-06 | 01 | 1 | SAFE-04 | — | Never return ('check', 0) | integration | `grep -c "check.*0" players/mtt_bot.py` returns 0 | ❌ W0 | ⬜ pending |
| 1-01-07 | 01 | 1 | SAFE-05 | — | Raises capped at stack | integration | Engine simulation | ❌ W0 | ⬜ pending |
| 1-01-08 | 01 | 1 | SAFE-06 | — | Picklable state | integration | `python -c "import pickle; from players.mtt_bot import HawkEyeBot; b=HawkEyeBot(); pickle.dumps(b)"` | ❌ W0 | ⬜ pending |
| 1-01-09 | 01 | 1 | SAFE-07 | — | _guard validates actions | integration | Engine simulation | ❌ W0 | ⬜ pending |
| 1-01-10 | 01 | 1 | STATE-01 | — | Pot accumulator tracks pot | integration | Engine simulation | ❌ W0 | ⬜ pending |
| 1-01-11 | 01 | 1 | STATE-02 | — | Hand boundary detection | integration | Engine simulation | ❌ W0 | ⬜ pending |
| 1-01-12 | 01 | 1 | STATE-03 | — | Preflop aggressor flag | integration | Engine simulation | ❌ W0 | ⬜ pending |
| 1-01-13 | 01 | 1 | STATE-04 | — | Hand counter | integration | Engine simulation | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `players/mtt_bot.py` — Bot file created with HawkEyeBot class

*No test framework to install — validation is through engine simulation.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Pot accumulator accuracy | STATE-01 | Requires examining game state during play | Run simulation, check bot doesn't make decisions based on wrong pot sizes |
| Hand boundary resets | STATE-02 | Requires cross-hand state inspection | Run simulation, verify hand counter increments |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
