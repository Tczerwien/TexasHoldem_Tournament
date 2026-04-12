---
phase: 02-preflop-engine
reviewed: 2026-04-10T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - players/mtt_bot.py
  - tests/test_preflop.py
  - tests/test_bot_safety.py
  - tests/test_bot_state.py
findings:
  critical: 0
  warning: 5
  info: 3
  total: 8
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-04-10
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

The preflop engine in `players/mtt_bot.py` is structurally sound: lookup tables build cleanly at module level, the push-fold / shallow / deep/medium branching is complete, `_guard` enforces all safety contracts, and the top-level try/except in `get_action` prevents crashes from escaping. No critical security or correctness issues were found.

Five warnings were identified:

1. A logic gap means certain villain shoves in push-fold mode are handled by the wrong code branch, causing miscalculated `villain_bb` for the CALL_TABLE lookup.
2. The `_detect_situation` helper has an ambiguous boundary that produces the wrong label when the big blind equals the small blind (e.g., in heads-up play or misconfigured states).
3. `_get_chen_key` and the preflop decision functions index `hole_cards[0]` and `hole_cards[1]` without a length check, so a malformed engine state (fewer than 2 cards) will crash inside `_decide` rather than being caught at the data boundary.
4. The 3-bet sizing comment in the deep/medium `facing_open` branch is misleading and may indicate a sizing error depending on how the engine interprets the `amount` parameter.
5. Both non-preflop test files (`test_bot_safety.py`, `test_bot_state.py`) construct hole cards with invalid treys integers (missing prime factor and rank-bit-in-high-word), making those test helpers inaccurate if used to exercise code that reads card fields beyond rank.

Three info items cover minor code clarity issues.

---

## Warnings

### WR-01: Push-fold shove detection misroutes limps and small opens

**File:** `players/mtt_bot.py:711`

**Issue:** In push-fold mode, the bot detects a villain shove as `call_amount >= stack * 0.5`. If an opponent limps or makes a small open (e.g., min-raise to 40 chips) while hero's stack is 280, `call_amount=40 < 140`, so the action falls through to the `facing_open` / `facing_3bet` branch (lines 728–734), which also uses `CALL_TABLE`. However, `villain_bb` is computed identically in that branch — so the practical effect is limited. The real risk is the *reverse*: if hero stack is very short (e.g., 60 chips) and villain shoves for 58 chips, `58 >= 30` triggers the shove branch correctly; but if hero stack is 62 and villain shoves 60, `60 >= 31` is True, correct. The threshold works correctly for the intended scenario but is semantically fragile: the comment says "facing a shove" but the condition triggers on any bet >= 50% of hero stack, which is not the same thing and can silently mix shove-vs-open decisions.

**Fix:** Use a sentinel comparison that checks whether `call_amount` represents an all-in or near-all-in for the villain rather than the hero's stack fraction:
```python
# Push-fold: detect whether villain is effectively all-in
# Use call_amount > 8 * bb as proxy for "villain shoved"
# (8BB+ call in push-fold territory means villain committed significant stack)
if call_amount > bb * 8:
    villain_bb = call_amount / bb if bb > 0 else 999
    if CALL_TABLE.get(chen_key, 0) >= villain_bb:
        return self._guard("call", 0, game_state)
    else:
        return self._guard("fold", 0, game_state)
```
Alternatively, pass villain stack size via game state if the engine exposes it.

---

### WR-02: `_detect_situation` returns wrong label when bb == sb

**File:** `players/mtt_bot.py:636-638`

**Issue:** `sb_complete` is detected by `call_amount == bb - sb`. If `bb == sb` (e.g., both blinds are 10 in some engine configurations, or heads-up where blinds are equal), then `bb - sb == 0`, which equals the `call_amount == 0` check for `bb_option`. Because `bb_option` is tested first (line 635), the `sb_complete` branch is never reached when `bb == sb`, and a SB complete situation is misclassified as `bb_option`. In heads-up play, both these mis-labels lead to the same action (check/call for free), so the practical impact is low but the routing is semantically wrong and could cause incorrect behavior if future code distinguishes these situations.

**Fix:** Add an explicit heads-up / equal-blind guard, or document the assumption:
```python
def _detect_situation(self, game_state):
    call_amount = game_state["call_amount"]
    bb = game_state["blinds"]["big"]
    sb = game_state["blinds"]["small"]
    if call_amount == 0:
        return "bb_option"
    # Only treat as sb_complete if sb < bb (standard structure)
    elif sb < bb and call_amount == bb - sb:
        return "sb_complete"
    elif call_amount == bb:
        return "rfi"
    elif call_amount < bb * 6:
        return "facing_open"
    else:
        return "facing_3bet"
```

---

### WR-03: No length guard on `hole_cards` before indexing

**File:** `players/mtt_bot.py:605-611`

**Issue:** `_get_chen_key`, `_is_3bet_hand`, `_is_4bet_hand`, `_is_premium`, and `_preflop` all access `hole_cards[0]` and `hole_cards[1]` without checking `len(hole_cards) >= 2`. If the engine passes a malformed state (empty list, single card), an `IndexError` is raised inside `_decide`. This is caught by the top-level `get_action` try/except (line 467), which is the correct safety net, but the error is silently swallowed — the bot folds or calls without any indication that something is wrong. The 500ms budget is unaffected, but silent failure on data corruption is a quality risk.

**Fix:** Add an early guard in `_preflop` (or in each helper) and log/return a safe default:
```python
def _preflop(self, game_state, est_pot):
    hole_cards = game_state["hole_cards"]
    if len(hole_cards) < 2:
        # Malformed state -- fall back safely
        return self._guard("fold", 0, game_state)
    # ... rest of method
```

---

### WR-04: 3-bet sizing comment is misleading; may indicate a sizing error

**File:** `players/mtt_bot.py:823-825`

**Issue:** The comment reads `# 3x the open: amount = call_amount * 2`. This is only correct if the engine interprets `('raise', amount)` as "raise BY amount" (so total bet = call_amount + amount = 3 * call_amount). If the engine interprets `amount` as the total to put in (i.e., "raise TO amount"), then `amount = call_amount * 2` would make the total bet only 2x the open, not 3x. This is a documentation ambiguity that could mask a sizing bug. The CLAUDE.md documentation refers to `('raise', amount)` without specifying raise-by vs raise-to, and the `_preflop_raise_amount` helper comment on line 669 says "Engine does: total_to_put_in = call_amount + amount", which confirms raise-BY semantics — but this comment is not duplicated at the usage site.

**Fix:** Replace the magic formula with a named variable and a clear comment:
```python
# 3-bet to ~3x the open. Engine uses raise-BY semantics:
# total_to_put_in = call_amount + amount
# So to make total = 3 * call_amount: amount = 2 * call_amount
threex_amount = call_amount * 2
return self._guard("raise", threex_amount, game_state)
```
Also confirm with the engine interface that raise-BY semantics hold (it's only stated in one inline comment).

---

### WR-05: Test helpers construct invalid treys card integers

**File:** `tests/test_bot_safety.py:64-65`, `tests/test_bot_state.py:43`

**Issue:** Both non-preflop test files build "premium" and "default" hole cards manually without the rank-bit-in-high-word (`1 << rank_int << 16`) that is part of the treys encoding. For example:

- `test_bot_safety.py:64`: `ace1 = (12 << 8) | (1 << 12) | 0x01` — missing `(1 << 12 << 16)`, so the rank high-bit field is 0 instead of `0x1000_0000`.
- `test_bot_state.py:43`: `hole_cards = [0x00000000, 0x00000500]` — both cards have `rank_int = 0` (2-rank) extracted via `(card >> 8) & 0xF`, but also have no prime factor, so any code path that multiplies primes (e.g., a future flush/hand evaluator) would produce incorrect results.

The `_get_chen_key` and `_is_premium` methods only extract rank via `(card >> 8) & 0xF` and suit via `(card >> 12) & 0xF`, so these tests pass today. However, if Phase 3 adds hand evaluation that reads the high-word rank bits or the prime field, these test helpers will produce wrong inputs and tests will pass with garbage data.

The `test_preflop.py` helper (`make_card`) is correct — it includes all fields. The other two test files should adopt the same pattern.

**Fix:** Replace the ad-hoc card construction in both files with the same `make_card` helper used in `test_preflop.py`:
```python
_PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41]

def make_card(rank_int, suit_int):
    return (1 << rank_int << 16) | (suit_int << 12) | (rank_int << 8) | _PRIMES[rank_int]

# Ace of spades:  make_card(12, 1)
# 7 of hearts:    make_card(5, 2)
# 2 of spades:    make_card(0, 1)
```
Move this helper to a shared `tests/helpers.py` module to avoid the duplication that caused this inconsistency.

---

## Info

### IN-01: `_is_premium` duplicates rank-extraction logic from `_get_chen_key`

**File:** `players/mtt_bot.py:598-601`

**Issue:** `_is_premium` uses a different rank encoding formula (`((card >> 8) & 0xF) + 2`) compared to `_get_chen_key` (`(card >> 8) & 0xF`). The `+2` offset in `_is_premium` means it operates on display ranks (2–14) while `_get_chen_key` operates on rank integers (0–12). Both are consistent within their own usage, but this dual convention is a latent source of confusion and off-by-two bugs if `_is_premium` is ever refactored to use `_get_chen_key`.

**Fix:** Migrate `_is_premium` to use rank_int (0-indexed) consistent with `_get_chen_key`, or add a comment documenting the convention difference:
```python
def _is_premium(self, hole_cards):
    # rank_int: 0=2, 1=3, ..., 12=A. Premium = pocket pair rank_int >= 10 (QQ+)
    r1 = (hole_cards[0] >> 8) & 0xF
    r2 = (hole_cards[1] >> 8) & 0xF
    return r1 == r2 and r1 >= 10  # QQ(10), KK(11), AA(12)
```

---

### IN-02: Fallback branches in `_preflop` are unreachable

**File:** `players/mtt_bot.py:737`, `players/mtt_bot.py:793`, `players/mtt_bot.py:841`

**Issue:** Each stack-mode block ends with `return self._guard("fold", 0, game_state)`. Given that `_detect_situation` returns one of exactly five values (`bb_option`, `sb_complete`, `rfi`, `facing_open`, `facing_3bet`) and every block handles all five, these fallback lines are unreachable. They are harmless safety nets but constitute dead code that adds noise.

**Fix:** Either document them explicitly as defensive dead code:
```python
# Defensive fallback -- all situations are handled above
return self._guard("fold", 0, game_state)
```
Or add an assertion that makes the unreachability explicit during development:
```python
# Should never reach here
assert False, f"Unhandled situation: {situation}"
```
Note: the assertion approach should be removed before production since it would trigger the top-level except and return a blind fold.

---

### IN-03: `random` module imported nowhere but listed as allowed

**File:** `players/mtt_bot.py` (module level)

**Issue:** The CLAUDE.md project spec repeatedly emphasizes that `random.sample` is the critical performance tool for Phase 3 Monte Carlo. It is not imported in the current file. This is expected at Phase 2 but worth noting so Phase 3 implementation does not forget to add `import random` at the module level (alongside `import math`).

**Fix:** Add `import random` as a commented placeholder at the top of `mtt_bot.py` to signal Phase 3's dependency:
```python
import math
import random  # Phase 3: MC equity estimation
```

---

_Reviewed: 2026-04-10_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
