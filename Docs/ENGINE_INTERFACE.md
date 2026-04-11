# ENGINE_INTERFACE.md
# MTT Pokerbot Engine — Verified Interface Reference
# IIT Poker Club Tournament 2026

**Status:** Fully verified against engine source code. Audit-reviewed April 10, 2026.
**Sources:** main.py, table.py, player_interface.py, config.py, sim_2.json
**Changelog:** v2.1 — Added pot_size bug documentation (Section 9a), heads-up blind quirk (9b),
draw bug (9c), check action warning (9d), pickling requirement (9e), import form warning (Section 3).

---

## 1. Verification Legend

| Tag | Meaning |
|-----|---------|
| `[VERIFIED]` | Confirmed directly from engine source code or simulation data |
| `[IMPLEMENTATION]` | Design recommendation for our bot |
| `[OPEN QUESTION]` | Still unresolved — requires local testing |

---

## 2. CRITICAL: Bot Must Be a Class

This is the single most important structural requirement.

The engine loader in `main.py` scans for classes only:
```python
for name, obj in inspect.getmembers(module, inspect.isclass):
    if issubclass(obj, Bot) and obj is not Bot:
        bots.append(obj())
```

A standalone `def get_action():` function is **completely invisible** to this loader.
The bot will never be registered, never play a hand, and score zero.

### Required Structure `[VERIFIED]`

```python
from engine.player_interface import Bot   # REQUIRED

class MyBot(Bot):
    def __init__(self):
        super().__init__("MyBotName")   # Name shown in results CSV

    def get_action(self, game_state):
        return ('call', 0)              # Minimum viable bot
```

---

## 3. Allowed Libraries `[VERIFIED from main.py]`

```python
ALLOWED_MODULES = {'math', 'random', 'numpy', 'pandas', 'engine.player_interface'}
```

```python
# SAFE TO USE:
from engine.player_interface import Bot    # Required — use THIS exact form (see warning below)
import math
import random
import numpy as np
# import pandas as pd                      # Allowed but likely not needed

# NEVER IMPORT — bot will be blocked for all 10 simulations:
# import os, sys, subprocess, socket
# import time                              # BLOCKED — use iteration caps instead
# import collections, itertools, functools # BLOCKED
# import treys                             # BLOCKED
# import sklearn, scipy, torch, cv2       # BLOCKED
```

The engine uses AST scanning to check imports before loading. Any blocked import
kills the bot per simulation — blocked in each of the 10 simulations independently,
resulting in zero score across all 10.

### ⚠️ Import Form Warning `[VERIFIED]`

The AST scanner treats `import X` and `from X import Y` differently:

```python
# CORRECT — allowed:
from engine.player_interface import Bot

# WRONG — blocked even though it looks similar:
import engine.player_interface    # 'engine' is not in ALLOWED_MODULES → BLOCKED
```

The check for `from X import Y` tests both the base module (`engine`) AND the full
module path (`engine.player_interface`). Since `engine.player_interface` is in
`ALLOWED_MODULES`, the `from` form passes. The bare `import` form only tests the
base module (`engine`), which is not in `ALLOWED_MODULES` and is blocked.

---

## 4. Tournament Configuration `[VERIFIED from config.json]`

```
simulation_count:       10
bot_decision_timeout:   500ms (hard cutoff)
starting_stack:         1500 chips
max_players_per_table:  9
hands_per_level:        20 rounds
antes:                  NONE (not in config)
```

### Blind Schedule `[VERIFIED]`

| Level | Small | Big | Stack in BB (1500 chips) | Players alive (approx) |
|-------|-------|-----|--------------------------|------------------------|
| 1     | 10    | 20  | **75BB**                 | 52                     |
| 2     | 15    | 30  | 50BB                     | ~52                    |
| 3     | 25    | 50  | 30BB                     | ~51                    |
| 4     | 50    | 100 | **15BB** ← push-fold threshold | ~51             |
| 5     | 100   | 200 | 7.5BB                    | ~48 — eliminations start |
| 6     | 200   | 400 | 3.75BB                   | ~36 — rapid eliminations |
| 7     | 300   | 600 | 2.5BB                    | ~20                    |
| 8     | 500   | 1000| 1.5BB                    | ~12                    |
| 9     | 1000  | 2000| 0.75BB                   | ~9                     |
| 10    | 2000  | 4000| —                        | ~5                     |
| 11    | 5000  | 10000| —                       | ~3 (bubble/ITM)        |

**Key insight from sim data:** An individual bot plays approximately 100–150 hands
per simulation. Deep-stack play is relevant for the first ~60 hands (Levels 1–3).
Push-fold dominates from Level 4 onward for average stacks.
The bubble (top 3 remaining) is typically reached around hand 120–140 of individual play.

---

## 5. game_state — Complete Field Reference

### Confirmed Fields `[VERIFIED from table.py]`

Exact state dict the engine constructs and passes to every bot:

```python
state = {
    "hole_cards":     player.hole_cards,
    "board_cards":    board,
    "pot_size":       sum(p.current_bet for p in players) + pot_manager.get_total_amount(),
    "stack_size":     player.stack,
    "call_amount":    call_amount,
    "min_raise":      min_raise,
    "blinds":         blinds,            # {"small": int, "big": int}
    "active_players": count,
}
```

| Field | Type | Description |
|-------|------|-------------|
| `hole_cards` | `list[int]` | Our 2 private cards as treys integers |
| `board_cards` | `list[int]` | 0–5 community cards as treys integers |
| `pot_size` | `int` | **⚠️ CURRENT-STREET BETS ONLY — NOT total pot.** See Section 9. |
| `stack_size` | `int` | Our remaining chip stack |
| `call_amount` | `int` | Chips needed to call. **0 = free check.** |
| `min_raise` | `int` | Minimum raise-by amount (starts at BB, increases with raises) |
| `blinds` | `dict` | `{"small": int, "big": int}` — current blind level |
| `active_players` | `int` | Players still active in this hand, **including all-in players** (not tournament total) |

### Confirmed Absent Fields `[VERIFIED — NOT IN game_state]`

| Field | Status | How to work around it |
|-------|--------|-----------------------|
| `position` | ABSENT (docstring in player_interface.py is wrong) | Infer from call_amount and blinds |
| `players_remaining` | ABSENT | Infer from blind level |
| `opponent_stacks` | ABSENT | Not available |
| `action_history` | ABSENT | Not available |
| `blind_level` | ABSENT | Infer from `blinds['big']` value |

---

## 6. Legal Actions `[VERIFIED]`

### Return Formats

```python
return ('fold', 0)      # Fold the hand — only when call_amount > 0
return ('call', 0)      # Call the bet, OR check if call_amount == 0
return ('raise', X)     # Raise — X is the raise-BY amount (not raise-to)
```

### Raise Is RAISE-BY `[VERIFIED from table.py]`

```python
# Engine source (table.py):
total_to_put_in = call_amount + amount    # amount = our raise-BY value
actual_bet = player.bet(total_to_put_in)
```

**Practical formula:**
```python
# To raise to a specific total amount this street:
def make_raise_action(target_total, call_amount, min_raise):
    raise_by = max(target_total - call_amount, min_raise)
    return ('raise', raise_by)

# Examples:
# Preflop, BB=20, want to raise to 50 total: ('raise', 30) — puts in 20+30=50
# Facing 100 bet, want to raise to 300 total: ('raise', 200) — puts in 100+200=300
```

### Raise Below Minimum `[VERIFIED — Gracefully Handled]`

```python
# Engine source (table.py):
if amount is None or amount < min_raise:
    amount = min_raise    # Silent correction, no penalty
```

We do not need to validate raise amounts against min_raise — the engine handles it.

---

## 7. Edge Cases — Verified Handling

### EC-1: Free Check (call_amount == 0) `[VERIFIED]`

```python
# Engine source — fold ONLY fires when call_amount > 0:
if action == "fold" and call_amount > 0:
    player.is_active = False
# When call_amount == 0: fold falls to else branch, engine logs as "check"
```

Returning `('fold', 0)` when `call_amount == 0` does NOT fold you — engine checks.
But always check explicitly:

```python
call_amount = game_state['call_amount']
if call_amount == 0:
    return ('call', 0)   # Explicit check
```

### EC-2: All-In Call (stack < call_amount) `[VERIFIED]`

```python
# Engine source (player_state.py):
actual_bet = min(amount, self.stack)   # Capped automatically
```

Just return `('call', 0)` — engine caps the call at your remaining stack.

### EC-3: Stack Too Small to Raise `[VERIFIED]`

If `stack_size < min_raise`, you cannot raise legally.
Engine will correct any raise-by amount below min_raise, but if your stack is less
than min_raise you effectively cannot make a meaningful raise.
Just call or fold in this situation.

### EC-4: Big Blind Option `[VERIFIED]`

When you are the BB and no one raised: `call_amount == 0`.
You may check (call) or raise. Never fold.

### EC-5: Exception in get_action `[VERIFIED]`

```python
# Engine source (table.py):
except Exception as e:
    action, amount = "fold", 0    # Forced fold
```

### EC-6: Timeout `[VERIFIED]`

```python
except concurrent.futures.TimeoutError:
    action, amount = "fold", 0    # Forced fold
```

### Master Safety Guard `[IMPLEMENTATION]`

```python
from engine.player_interface import Bot

class MyBot(Bot):
    def __init__(self):
        super().__init__("MyBot")

    def get_action(self, game_state):
        try:
            return self._decide(game_state)
        except Exception:
            # Never crash — fallback to safe action
            if game_state.get('call_amount', 1) == 0:
                return ('call', 0)   # Free check
            return ('fold', 0)       # Fold safely

    def _decide(self, game_state):
        # All logic here
        pass
```

---

## 8. Card Encoding — Treys Integers `[VERIFIED]`

Cards arrive as treys library integers. The bot cannot import treys.
Decode manually using bit operations.

### Decoder `[VERIFIED against live engine data]`

```python
def get_rank(card_int):
    """
    Returns rank as int: 2=Two ... 10=Ten, 11=J, 12=Q, 13=K, 14=A
    """
    return ((card_int >> 8) & 0xF) + 2

def get_suit(card_int):
    """
    Returns suit: Spades=1, Hearts=2, Diamonds=4, Clubs=8
    """
    return (card_int >> 12) & 0xF

SPADES, HEARTS, DIAMONDS, CLUBS = 1, 2, 4, 8
```

### Verification (tested against real sim_2.json data)

| Integer | Decoded | Correct |
|---------|---------|---------|
| 8398611 | 9♥ | ✅ |
| 164099 | 3♣ | ✅ |
| 69634 | 2♠ | ✅ |
| 139523 | 3♥ | ✅ |

### Useful Helpers

```python
def ranks(cards):
    """Sorted ranks, highest first."""
    return sorted([get_rank(c) for c in cards], reverse=True)

def suited(hole_cards):
    """True if both hole cards share a suit."""
    return get_suit(hole_cards[0]) == get_suit(hole_cards[1])

def is_pocket_pair(hole_cards):
    return get_rank(hole_cards[0]) == get_rank(hole_cards[1])

def board_has_flush_draw(hole_cards, board_cards):
    """True if we have 4+ cards to a flush."""
    all_cards = hole_cards + board_cards
    for suit in [SPADES, HEARTS, DIAMONDS, CLUBS]:
        if sum(1 for c in all_cards if get_suit(c) == suit) >= 4:
            return True
    return False

def has_pair_on_board(board_cards):
    """True if two board cards share a rank."""
    board_ranks = [get_rank(c) for c in board_cards]
    return len(board_ranks) != len(set(board_ranks))

def board_is_monotone(board_cards):
    """True if all board cards share a suit."""
    if len(board_cards) < 3:
        return False
    suits = [get_suit(c) for c in board_cards]
    return len(set(suits)) == 1
```

---

## 9. Known Engine Quirks `[VERIFIED]`

These are confirmed behaviors in the engine source code that differ from what
a bot author might naively expect. All three must be accounted for in the bot.

---

### 9a. pot_size Is Broken on Postflop Streets `[VERIFIED — CRITICAL BUG]`

**This is the single most important implementation hazard in the entire codebase.**

`pot_size` is computed as:
```python
sum(p.current_bet for p in self.players) + pot_manager.get_total_amount()
```

At the end of every betting round, all `current_bet` values are reset:
```python
for p in self.players:
    p.current_bet = 0
```

And `pot_manager.collect_bets()` is only called at showdown — so
`pot_manager.get_total_amount()` equals **0** during every betting round.

**Result:** At the start of the flop, `pot_size = 0`, regardless of how much
was bet preflop. All chips from previous streets are invisible.

| Street | What pot_size shows | Actual pot |
|--------|---------------------|------------|
| Preflop | Correct — current bets | = pot_size |
| Flop start | 0 — preflop chips invisible | pot_size + preflop pot |
| Flop, after bet | Only flop bets | pot_size + preflop pot |
| Turn | Only turn bets | pot_size + preflop + flop pot |
| River | Only river bets | pot_size + prior streets |

**Any pot odds calculation using raw `pot_size` on postflop streets is wrong.**
Do not use `pot_size` for pot odds after the flop.

**Required workaround** — track total pot via instance state:

```python
class MyBot(Bot):
    def __init__(self):
        super().__init__("MyBot")
        self._street_pot_accumulator = 0   # chips from completed streets
        self._last_street = -1             # board_cards length last seen
        self._hand_start_stack = None      # stack when hand began

    def get_action(self, game_state):
        street = len(game_state['board_cards'])
        stack = game_state['stack_size']

        # Detect new hand (board is empty, or stack jumped from winnings)
        if street == 0 and self._last_street != 0:
            self._street_pot_accumulator = 0
            self._hand_start_stack = stack

        # Detect new street — previous street's pot is now invisible
        if street != self._last_street and street > 0:
            # pot_size just before street change was the full previous-street pot
            # We can't capture it perfectly, but we can approximate:
            self._street_pot_accumulator += game_state['pot_size']
            # Note: this misses any bets made AFTER our last action on the prior street

        self._last_street = street

        # Use this for all pot odds calculations:
        estimated_total_pot = self._street_pot_accumulator + game_state['pot_size']

        # ... rest of decision logic using estimated_total_pot ...
```

**Important caveat:** This workaround is an approximation. The bot only observes
`pot_size` at its own decision points. Bets made by opponents *after* the bot
acts on a given street are included in the next street's `pot_size` starting value
but may not be captured by this accumulator. The error is bounded — typically
one opponent's bet — and is acceptable for v1 strategy decisions.

**Simplest safe approach for v1:** Avoid pot odds calculations entirely on the
flop. Use hand strength thresholds instead of pot odds as the primary decision
driver. Only use pot odds (with the accumulator) on turn and river.

---

### 9b. Heads-Up Blind Structure Is Non-Standard `[VERIFIED]`

When exactly 2 players remain, the engine uses this logic:
```python
bb_idx = (self.button_idx + 2) % num_players if num_players > 2 else self.button_idx
```

With `num_players == 2`: `bb_idx = self.button_idx` — **the button posts the big blind.**

Standard heads-up poker: button = SB (posts less, acts first preflop).
This engine: button = BB (posts more, acts second preflop since action starts at sb_idx).

**Effect:** The button bleeds chips faster in heads-up play than standard poker.
The non-button has a cost advantage of (BB - SB) chips per orbit.

**Impact on strategy:** When heads-up, do not assume standard button = positional
advantage in terms of blind cost. Adjust heads-up aggression accordingly — the
non-button position is actually cheaper to play.

---

### 9c. Turn and River Card Draw Wastes One Card Per Street `[VERIFIED — BENIGN]`

The engine's turn/river draw code:
```python
drawn = deck.draw(1) if isinstance(deck.draw(1), int) else deck.draw(1)[0]
```

This calls `deck.draw(1)` twice — once for the `isinstance` check and once for
the actual assignment. The card from the first call is discarded.

**Impact:** Each street (turn, river, and runout) consumes 2 cards instead of 1.
Since the deck is shuffled, all remaining cards are equally likely regardless of
which card was discarded. **No bot action needed.** This is a cosmetic bug with
no strategic consequence.

---

### 9d. `('check', 0)` Is Not a Valid Action String `[VERIFIED]`

The engine's action processing only checks for `'fold'`, `'call'`, and `'raise'`.
The string `'check'` is not recognized and falls to the `else` branch:

```python
else:
    if call_amount > 0:
        player.is_active = False   # ← FOLDS YOU
    else:
        # logs as check
```

**If `call_amount > 0` and you return `('check', 0)`, you will be folded.**
Always use `('call', 0)` for both checking and calling.

---

### 9e. Instance State Must Be Picklable `[VERIFIED]`

The engine uses `ProcessPoolExecutor` which serializes bot objects via pickle
for multiprocessing. Any non-picklable instance attribute will cause the bot
to fail silently in a worker process.

**Keep all `self.x` attributes as basic Python types:**
```python
# Safe:
self._hand_count = 0         # int
self._pot_accumulator = 0    # int / float
self._opponent_data = {}     # dict of basic types
self._hand_cards = []        # list of ints

# Risky (may not pickle):
# self._func = lambda x: x   # lambda functions
# self._file = open(...)      # file handles
# self._lock = threading.Lock() # threading objects
```

---

## 10. Instance State and Precomputation `[VERIFIED]`

### Instance State Persists Within a Simulation

```python
class MyBot(Bot):
    def __init__(self):
        super().__init__("MyBot")
        self._hand_count = 0          # Increments across ALL hands in simulation
        self._opponent_model = {}     # Tracks opponents across all hands
```

Each simulation gets a fresh `__init__()`. State does NOT carry over between simulations.

### Precomputation Is Free (Runs Before 500ms Clock) `[VERIFIED]`

```python
# Module-level code runs once at import time, before any action calls
# This is NOT counted against the 500ms budget

def _build_preflop_table():
    # Can be slow — runs once only
    table = {}
    # ... build lookup tables ...
    return table

PREFLOP_TABLE = _build_preflop_table()    # Free computation
PUSH_FOLD_TABLE = _build_push_fold_table() # Free computation

class MyBot(Bot):
    def get_action(self, game_state):
        hand = classify_hand(game_state['hole_cards'])
        return PREFLOP_TABLE[hand]   # Instant dict lookup
```

---

## 11. Tournament Stage and Stack Mode Detection `[IMPLEMENTATION]`

### Stack Mode (Primary Decision Driver)

```python
def get_stack_mode(game_state):
    """Drives strategy mode. More reliable than tournament stage."""
    stack_bb = game_state['stack_size'] / game_state['blinds']['big']

    if stack_bb >= 40:   return 'deep'
    if stack_bb >= 25:   return 'medium'
    if stack_bb >= 15:   return 'shallow'
    return 'push_fold'
```

### Tournament Stage (Overlay for ICM Adjustments)

```python
def get_stage(game_state):
    """
    Estimates tournament stage from blind level.
    Confirmed from sim_2.json: rapid eliminations start at 200/400 (Level 6).
    Bubble (top 3) typically at Level 8+ (blinds 500/1000+).
    """
    bb = game_state['blinds']['big']

    if bb <= 50:    return 'early'    # Level 1-3: full field
    if bb <= 200:   return 'middle'   # Level 4-5: stacks compressing
    if bb <= 600:   return 'late'     # Level 6-7: rapid eliminations
    return 'bubble'                   # Level 8+: near final table
```

---

## 11. Competition Intelligence `[VERIFIED from sim_2.json]`

### Current Test Field (52 bots)
- 50 TestBots: `random.choice([('call', 0), ('fold', 0)])` — call/fold only, never raise
- CallBot: always `('call', 0)` — never raises, never folds
- RandomBot: random actions including rare raises

### Key Statistics from Full Simulation (792 total hands)

| Metric | Value |
|--------|-------|
| Total raise actions across all tables | **17** |
| Bots that ever raised | **1** (RandomBot only) |
| TestBot_8 action with pocket Kings | Called BB, never raised |
| CallBot final position (sim 2) | 43rd of 52 |
| Raises as % of all actions | ~2.1% |

### What This Means for Strategy

1. **Blind stealing is nearly free**: A preflop raise will be folded to >80% of the time
2. **Value betting is unchallenged**: Opponents call with random hands, rarely fight back
3. **Nobody 3-bets**: Any open raise goes uncontested or gets called flat
4. **Passive play loses chips slowly**: CallBot bled chips and finished 43rd
5. **The real opponents are student submissions**: Unknown quality — build for both fields

---

## 12. Timing Reference `[IMPLEMENTATION]`

### 500ms Budget

| Phase | Allocation | Notes |
|-------|-----------|-------|
| Parsing game_state | 1ms | |
| Stack/stage mode detection | 1ms | |
| Preflop lookup | 1ms | Table lookups are instant |
| Postflop Monte Carlo | 250ms | Capped by iteration count |
| Decision logic | 10ms | Threshold comparisons |
| Safety checks | 1ms | |
| **Buffer (never touch)** | **236ms** | Safety margin |

### Time Control Without `time` Module

```python
# Cannot use: import time (blocked)
# Use fixed iteration counts instead:

FLOP_MC_ITERS = 300     # Benchmark and adjust
TURN_MC_ITERS = 400     # Fewer unknowns = faster per iter
RIVER_MC_ITERS = 500    # Or full enumeration (~990 combinations)

def postflop_equity(hole_cards, board_cards, n_opponents):
    street = len(board_cards)
    if street == 3:   iters = FLOP_MC_ITERS
    elif street == 4: iters = TURN_MC_ITERS
    else:             iters = RIVER_MC_ITERS

    wins = sum(_sim_once(hole_cards, board_cards, n_opponents)
               for _ in range(iters))
    return wins / iters
```

**Required action before finalizing:** Benchmark `_sim_once()` locally.
Target: `iters` × time_per_iter < 250ms.

---

## 13. Corrected Diagnostic Bot

Place this in `players/diagnostic_bot.py` and run `python main.py`:

```python
from engine.player_interface import Bot

class DiagnosticBot(Bot):
    """Reveals exact game_state structure. Delete before submission."""

    def __init__(self):
        super().__init__("DiagnosticBot")
        self._calls = 0

    def get_action(self, game_state):
        self._calls += 1

        if self._calls <= 5:
            with open('diagnostic_output.txt', 'a') as f:
                f.write(f'\n===== CALL #{self._calls} =====\n')

                # All keys and values
                for key, val in game_state.items():
                    f.write(f'  {key}: {val!r}  (type={type(val).__name__})\n')

                # Persistence test
                f.write(f'\nCall counter: {self._calls} '
                        f'(should increment — proves instance state persists)\n')

                # Decode hole cards
                f.write('\nDecoded hole cards:\n')
                for c in game_state['hole_cards']:
                    rank = ((c >> 8) & 0xF) + 2
                    suit = (c >> 12) & 0xF
                    rn = {14:'A',13:'K',12:'Q',11:'J',10:'T'}.get(rank, str(rank))
                    sn = {1:'s',2:'h',4:'d',8:'c'}.get(suit, f'?{suit}')
                    f.write(f'  {c} -> {rn}{sn}\n')

                # Check for bonus fields
                f.write('\nBonus field check:\n')
                for field in ['position','players_remaining','opponent_stacks',
                              'action_history','blind_level','seat','num_players']:
                    val = game_state.get(field, 'NOT PRESENT')
                    f.write(f'  {field}: {val}\n')

        # Safe default
        if game_state['call_amount'] == 0:
            return ('call', 0)
        return ('fold', 0)
```

---

## 14. Open Questions Checklist

All previously open questions are resolved. The items below track the audit-confirmed
requirements that must be implemented — not questions about the engine.

| Question | Status |
|----------|--------|
| Exact game_state fields | ✅ VERIFIED — 8 fields only |
| `position` available | ✅ VERIFIED — ABSENT |
| `players_remaining` available | ✅ VERIFIED — ABSENT |
| Raise = raise-by or raise-to | ✅ VERIFIED — RAISE-BY |
| Fold with free check behavior | ✅ VERIFIED — engine checks instead |
| `time` module available | ✅ VERIFIED — BLOCKED |
| Instance state persists | ✅ VERIFIED — yes, within simulation |
| Import-time separate from 500ms | ✅ VERIFIED — yes, safe to precompute |
| Raise below min_raise behavior | ✅ VERIFIED — silently corrected |
| Card decoder correct | ✅ VERIFIED against 4 live data points |
| Antes exist | ✅ VERIFIED — NONE in config |
| pot_size shows full pot | ✅ VERIFIED — NO, current-street only (Section 9a) |
| Heads-up blind structure standard | ✅ VERIFIED — NO, button pays BB (Section 9b) |

**Required bot implementation items from this document:**
1. Bot MUST be a class inheriting from `Bot`
2. MUST use `from engine.player_interface import Bot` (not bare import)
3. MUST implement pot accumulator (Section 9a) — do not use `pot_size` directly for pot odds
4. MUST keep instance state picklable (Section 9e)
5. MUST use `('call', 0)` for checks, never `('check', 0)`

---

*Document version: 2.1 — Audit-reviewed and updated*
*Changes from v2.0: Added Section 9 (Known Engine Quirks), fixed pot_size description,*
*added import form warning, added active_players all-in note, updated checklist.*
*Next document: STRATEGY_REFERENCE.md*
