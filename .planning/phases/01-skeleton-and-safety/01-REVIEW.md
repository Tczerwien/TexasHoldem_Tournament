---
phase: 01-skeleton-and-safety
reviewed: 2026-04-10T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - players/mtt_bot.py
  - tests/test_bot_safety.py
  - tests/test_bot_state.py
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-04-10T00:00:00Z
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Reviewed the Phase 01 skeleton bot (`players/mtt_bot.py`) and its two test suites. The overall
structure is sound: the SAFE-02 outer exception wrapper correctly prevents crashes, the guard
function covers the required action-validation cases, and all instance attributes are plain Python
types satisfying pickling requirements.

Four warnings were found — all in the production bot file. None are crash risks in isolation
(SAFE-02 absorbs them), but two create implicit order-dependencies that will become latent bugs
when Phase 2 adds complexity. No critical security issues exist; this is a self-contained game-bot
with no I/O or external surfaces.

---

## Warnings

### WR-01: `_detect_new_hand` never updates `_last_board_len` — sentinel cannot clear without `_update_pot`

**File:** `players/mtt_bot.py:97-103`
**Issue:** The sentinel path (`_last_board_len == -1`) returns early at line 103 without updating
`_last_board_len`. The field is only updated inside `_update_pot` (line 133). As long as `_decide`
always calls `_update_pot` after `_detect_new_hand`, this works. But if either method is ever
called in isolation — or if the call order changes — the sentinel persists, and `_hand_num` will
stay at 0 forever (or rather at the value set when the sentinel path fires).

This is an implicit coupling between two methods: `_detect_new_hand` is correct only because
`_update_pot` always runs afterward. The sentinel should be cleared inside `_detect_new_hand`
itself to make the method self-contained.

**Fix:**
```python
def _detect_new_hand(self, game_state):
    board_len = len(game_state["board_cards"])

    if self._last_board_len == -1:
        # First call ever in this simulation (sentinel)
        self._hand_num = 1
        self._pot_total = 0
        self._street_pot = 0
        self._was_preflop_aggressor = False
        self._last_board_len = board_len  # <-- clear sentinel here
        return

    if board_len == 0 and self._last_board_len > 0:
        self._hand_num += 1
        self._pot_total = 0
        self._street_pot = 0
        self._was_preflop_aggressor = False
```

Note: if this change is made, `_update_pot` must guard against double-updating `_last_board_len`
or be adjusted so it does not reset the value set by `_detect_new_hand`.

---

### WR-02: Redundant dead-condition check creates misleading comment

**File:** `players/mtt_bot.py:160-166`
**Issue:** Inside the `if call_amount == 0:` branch, the code already confirmed
`len(board_cards) == 0` at line 160. The identical check at line 165 is always true and the
comment `# only set on preflop raises` is misleading — it implies the flag might not be set, but
it always will be at that point. The dead check is benign now but makes the intent confusing.

The same redundancy exists at line 171/175 in the facing-a-bet branch.

**Fix:**
```python
# Inside `if call_amount == 0:` block
if len(board_cards) == 0 and self._is_premium(hole_cards):
    big_blind = game_state["blinds"]["big"]
    raise_amt = max(min_raise, big_blind * 3)
    if raise_amt > stack_size:
        raise_amt = stack_size
    self._was_preflop_aggressor = True  # remove redundant len check
    return self._guard("raise", raise_amt, game_state)
```

---

### WR-03: `_is_premium` has no guard against empty or short `hole_cards`

**File:** `players/mtt_bot.py:192-193`
**Issue:** `hole_cards[0]` and `hole_cards[1]` are accessed without a length check. If the engine
passes an empty or single-card list (e.g., during a bot-elimination edge case or malformed state),
this raises `IndexError`. The SAFE-02 wrapper absorbs the exception, but the fallback behavior
differs depending on `call_amount`: if free, it returns `("call", 0)`; if facing a bet, it folds.
Silent absorption of a malformed state makes debugging harder in later phases.

**Fix:**
```python
def _is_premium(self, hole_cards):
    if len(hole_cards) < 2:
        return False
    r1 = ((hole_cards[0] >> 8) & 0xF) + 2
    r2 = ((hole_cards[1] >> 8) & 0xF) + 2
    return r1 == r2 and r1 >= 12
```

---

### WR-04: `make_premium_cards()` is duplicated across both test files with identical implementation

**File:** `tests/test_bot_safety.py:57-66` and `tests/test_bot_state.py:56-65`
**Issue:** The utility function is copied verbatim. If the treys encoding interpretation changes
(e.g., a Phase 2 discovery that the bit layout differs), both copies must be updated independently.
A missed update produces a silent test failure where `_is_premium` returns False for manufactured
"premium" cards.

**Fix:** Extract to a shared `tests/helpers.py` module and import from both test files:
```python
# tests/helpers.py
def make_premium_cards():
    ace1 = (12 << 8) | (1 << 12) | 0x01
    ace2 = (12 << 8) | (2 << 12) | 0x02
    return [ace1, ace2]
```
```python
# tests/test_bot_safety.py
from helpers import make_premium_cards
```

---

## Info

### IN-01: `_guard` does bare key access on `game_state` without `KeyError` protection

**File:** `players/mtt_bot.py:53-55`
**Issue:** `game_state["call_amount"]`, `game_state["stack_size"]`, and `game_state["min_raise"]`
are accessed with bare dict indexing. A missing key raises `KeyError`, which propagates up through
`_decide` and is caught by SAFE-02. However, `_guard` is documented as the "last line of defense"
before returning — having it raise rather than degrade gracefully is inconsistent with that role.
This is low priority since the engine contract guarantees these keys, but worth noting for Phase 2
when game_state fields expand.

**Fix (optional for Phase 2):**
```python
call_amount = game_state.get("call_amount", 0)
stack_size = game_state.get("stack_size", 0)
min_raise = game_state.get("min_raise", 0)
```

---

### IN-02: No test exercises `_detect_new_hand` in isolation (without `_update_pot` following)

**File:** `tests/test_bot_state.py` (no specific line — test is absent)
**Issue:** WR-01 describes an implicit coupling where `_detect_new_hand` relies on `_update_pot`
to clear the sentinel. There is no test that calls `_detect_new_hand(state)` directly and then
checks that `_last_board_len` has been updated. All existing tests go through `get_action`, which
ensures `_update_pot` always follows. A unit test of the method in isolation would catch a
regression if the call order ever changes.

**Fix:** Add a test in `test_bot_state.py`:
```python
def test_detect_new_hand_clears_sentinel():
    bot = HawkEyeBot()
    gs = make_state(board_cards=[])
    bot._detect_new_hand(gs)
    assert bot._last_board_len == 0, "Sentinel should be cleared after first detect call"
```
(This test will currently fail until WR-01 is resolved.)

---

### IN-03: Mock engine setup is duplicated across both test files

**File:** `tests/test_bot_safety.py:13-27` and `tests/test_bot_state.py:12-27`
**Issue:** The `MockBot` class and `sys.modules` injection block are copied verbatim. Same
maintainability concern as WR-04 — a change to the engine interface (e.g., `Bot.__init__`
signature) requires updates in two places.

**Fix:** Move mock setup to `tests/helpers.py` or a `conftest.py` (if pytest is used) so it is
shared:
```python
# tests/conftest.py  (pytest auto-discovers this)
import sys, types

class MockBot:
    def __init__(self, name):
        self.name = name
    def get_action(self, game_state):
        raise NotImplementedError

mock_engine = types.ModuleType("engine")
mock_player_interface = types.ModuleType("engine.player_interface")
mock_player_interface.Bot = MockBot
sys.modules["engine"] = mock_engine
sys.modules["engine.player_interface"] = mock_player_interface
```

---

_Reviewed: 2026-04-10T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
