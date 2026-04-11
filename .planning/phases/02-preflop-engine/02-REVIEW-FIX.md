---
phase: 02-preflop-engine
fixed_at: 2026-04-10T00:00:00Z
review_path: .planning/phases/02-preflop-engine/02-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 02: Code Review Fix Report

**Fixed at:** 2026-04-10
**Source review:** .planning/phases/02-preflop-engine/02-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5
- Fixed: 5
- Skipped: 0

## Fixed Issues

### WR-01: Push-fold shove detection misroutes limps and small opens

**Files modified:** `players/mtt_bot.py`
**Commit:** 08750af
**Applied fix:** Replaced the hero-stack-fraction threshold (`call_amount >= stack * 0.5`) with a BB-based threshold (`call_amount > bb * 8`) for detecting villain shoves in push-fold mode. This uses a poker-meaningful criterion (8BB+ call in push-fold territory indicates significant villain commitment) rather than a fragile percentage of hero's stack.

### WR-02: `_detect_situation` returns wrong label when bb == sb

**Files modified:** `players/mtt_bot.py`
**Commit:** e551b17
**Applied fix:** Added `sb < bb` guard to the `sb_complete` branch in `_detect_situation`. When blinds are equal (e.g., heads-up or misconfigured states), `bb - sb == 0` which would conflict with the `call_amount == 0` check for `bb_option`. The guard ensures `sb_complete` only triggers under standard blind structure where sb < bb.

### WR-03: No length guard on `hole_cards` before indexing

**Files modified:** `players/mtt_bot.py`
**Commit:** 8f82e5d
**Applied fix:** Added an early guard `if len(hole_cards) < 2` at the top of `_preflop()` that returns a safe fold via `_guard`. This prevents `IndexError` from propagating if the engine passes a malformed state with fewer than 2 hole cards, catching the issue at the data boundary rather than deep inside helper methods.

### WR-04: 3-bet sizing comment is misleading; may indicate a sizing error

**Files modified:** `players/mtt_bot.py`
**Commit:** 750e757
**Applied fix:** Replaced the misleading comment `# 3x the open: amount = call_amount * 2` with a detailed explanation of the raise-BY semantics: `total_to_put_in = call_amount + amount`, so `amount = 2 * call_amount` makes `total = 3 * call_amount`. Also renamed the variable from `amt` to `threex_amount` for clarity.

### WR-05: Test helpers construct invalid treys card integers

**Files modified:** `tests/test_bot_safety.py`, `tests/test_bot_state.py`
**Commit:** a08a815
**Applied fix:** Added the `_PRIMES` constant and `make_card(rank_int, suit_int)` helper (matching the correct implementation in `test_preflop.py`) to both test files. Updated `make_state` default hole cards from raw hex literals (`0x00000000`, `0x00000500`) to `make_card(0, 1)` and `make_card(5, 2)`. Updated `make_premium_cards` from ad-hoc bit manipulation (missing high-word rank bit) to `make_card(12, 1)` and `make_card(12, 2)`. All cards now include the full treys encoding: rank-bit-in-high-word, suit bits, rank byte, and prime factor.

---

_Fixed: 2026-04-10_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
