---
phase: 05-tournament-awareness
reviewed: 2026-04-11T12:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - players/mtt_bot.py
  - tests/test_postflop_decisions.py
  - tests/test_tournament.py
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 5: Code Review Report

**Reviewed:** 2026-04-11T12:00:00Z
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Reviewed the tournament awareness implementation (Phase 5) across the main bot source and two test files. The bot logic in `mtt_bot.py` is well-structured with solid safety guards, proper division-by-zero protections in most places, and clean separation between preflop/postflop decision paths. The tournament stage detection, stack role classification, ICM multiplier, bubble adjustments, ITM aggression, heads-up play, and exploit adjustment all integrate cleanly into the existing decision engine.

Three warnings were found: (1) test setup code in `test_tournament.py` sets a nonexistent attribute name, failing to reset pot state as intended; (2) the non-aggressor has no flop betting path even for monster hands; (3) the draw detection logic misses a specific gutshot case involving ace-low straights. Two informational items relate to a redundant inner loop and a missing division-by-zero guard.

## Warnings

### WR-01: Test suite sets nonexistent attribute `_pot_accumulator` instead of `_pot_total`

**File:** `tests/test_tournament.py:185,240,294,331,383,414`
**Issue:** Six test `setUp` methods set `self.bot._pot_accumulator = 0`, but `HawkEyeBot` has no such attribute. The bot uses `_pot_total` and `_street_pot` for pot tracking. In Python, assigning to a nonexistent attribute silently creates a new instance attribute that the bot logic never reads. The tests believe they are resetting pot state to a clean baseline, but they are not. Currently the tests pass because the `_preflop` method (which most tournament tests exercise) does not depend on pot state, and the tests that call `_facing_bet` or `_bet_or_check` directly pass `est_pot` as a parameter, bypassing the pot accumulator entirely. However, if any future test routes through `_decide()` (which calls `_update_pot`), stale pot state from `__init__` may produce incorrect `est_pot` values, causing test failures that are hard to diagnose.
**Fix:**
Replace all 6 occurrences of `self.bot._pot_accumulator = 0` with the correct attribute names:
```python
self.bot._pot_total = 0
self.bot._street_pot = 0
```

### WR-02: Non-aggressor has no flop betting path, even with monster hands

**File:** `players/mtt_bot.py:1403-1421`
**Issue:** In `_bet_or_check`, the flop betting block (line 1404) requires `self._was_preflop_aggressor` to be True. The turn and river blocks (lines 1411, 1416) only fire for `street == 4` and `street == 5` respectively. This means a non-aggressor on the flop (street==3) with any EHS -- even 0.95 (a near-certain winner) -- will always check. There is no value betting path for the non-aggressor on the flop. This is a strategic logic gap: a player who called preflop and flopped a full house has no mechanism to build the pot on the flop.
**Fix:**
Add a flop value bet branch for non-aggressors with strong hands below the c-bet block:
```python
# POST-06: C-bet on flop when preflop aggressor
if street == 3 and self._was_preflop_aggressor:
    threshold = self._cbet_threshold(texture)
    if ehs >= threshold:
        bet_size = self._calc_bet_size(est_pot, stack, texture, street)
        return _apply_commit(bet_size)

# Non-aggressor flop value bet with strong hands
if street == 3 and ehs >= value_threshold:
    bet_size = self._calc_bet_size(est_pot, stack, texture, street)
    return _apply_commit(bet_size)
```

### WR-03: Ace-low straight draw not detected as gutshot

**File:** `players/mtt_bot.py:1131-1147`
**Issue:** In `_detect_draws`, when the ranks [-1, 0, 1, 2] (ace-low through 4) appear, the window has `span == 3` (4 consecutive ranks), so it enters the OESD branch (line 1138). The OESD check correctly rejects it because the low end (-2) fails `>= 0`. However, the code then falls through without flagging it as a gutshot. In reality, A-2-3-4 is a one-ended straight draw (needs a 5 to make A-2-3-4-5), which is strategically equivalent to a gutshot (4 outs). The `span == 4` gutshot branch (line 1145) is never reached because span is 3. This undervalues the draw bonus for ace-low straight draws, slightly reducing EHS.
**Fix:**
Add an else clause to the OESD path that flags a one-ended straight draw as a gutshot:
```python
if span == 3:
    low_end = unique_ranks[i] - 1
    high_end = unique_ranks[j] + 1
    if low_end >= 0 and high_end <= 12:
        has_oesd = True
    else:
        # One-ended straight draw (blocked on one side)
        has_gutshot = True
elif span == 4:
    has_gutshot = True
```

## Info

### IN-01: Redundant inner loop in draw detection

**File:** `players/mtt_bot.py:1133-1136`
**Issue:** The nested loop `for j in range(i + 3, len(unique_ranks))` immediately filters with `if j - i != 3: continue`, meaning only the case `j == i + 3` executes. This is functionally equivalent to `j = i + 3` with a bounds check, but the loop structure is misleading and performs unnecessary iterations for longer rank lists.
**Fix:**
Replace the inner loop with a direct index computation:
```python
for i in range(len(unique_ranks) - 3):
    j = i + 3
    span = unique_ranks[j] - unique_ranks[i]
    # ... rest of logic
```

### IN-02: No division-by-zero guard in `_get_stack_role` for `active_players`

**File:** `players/mtt_bot.py:659`
**Issue:** `_get_stack_role` computes `avg_stack = total_chips / n` where `n = game_state["active_players"]`. Unlike `_get_stack_mode` (which guards `bb == 0` on line 613-614), there is no guard for `n == 0`. In practice, the tournament engine should never provide `active_players == 0`, and the `get_action` try/except (SAFE-02) would catch a ZeroDivisionError. However, adding an explicit guard would be consistent with the defensive coding pattern used elsewhere.
**Fix:**
```python
n = game_state["active_players"]
if n <= 0:
    return "medium"  # safe default
avg_stack = total_chips / n
```

---

_Reviewed: 2026-04-11T12:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
