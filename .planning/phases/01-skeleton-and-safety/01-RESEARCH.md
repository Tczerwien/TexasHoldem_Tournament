# Phase 1: Skeleton and Safety - Research

**Researched:** 2026-04-10
**Domain:** MTT engine interface, bot safety infrastructure, state tracking
**Confidence:** HIGH

## Summary

Phase 1 creates a crash-proof bot skeleton that loads in the MTT engine, survives all 10 simulations, plays every hand legally, and tracks game state. Research focused on the exact engine interface by reading all source files: `player_interface.py`, `table.py`, `player_state.py`, `pot.py`, `config.py`, `tournament.py`, and `main.py`.

The engine has several critical quirks that directly impact safety requirements: (1) `pot_size` in `game_state` only reflects current-street bets because `pot_manager.collect_bets()` runs at showdown, not during betting rounds; (2) returning `('check', 0)` when facing a bet causes a silent fold because the engine's default handler folds on unrecognized actions when `call_amount > 0`; (3) the `position` key documented in `player_interface.py` is NOT actually included in the `game_state` dict built by `table.py`; (4) the engine uses `ProcessPoolExecutor` so the bot must be fully picklable.

**Primary recommendation:** Build the simplest possible bot that handles every engine edge case correctly, with a `_guard()` function as the last line of defense before returning any action tuple. Use tight-passive defaults (call if cheap, fold if expensive) with premium hand raises (AA/KK/QQ). All intelligence comes in later phases.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Tight-passive base strategy until Phase 2 adds real intelligence -- call when call_amount < 15% of stack, fold otherwise
- **D-02:** Raise with premium hands only (AA/KK/QQ) even in Phase 1, to avoid leaving obvious value on the table against the weak test field
- **D-03:** Always check when call_amount is 0 (never fold for free per SAFE-03)
- **D-04:** Class name `HawkEyeBot`, inherits from `Bot`
- **D-05:** Display name `"HawkEye"` passed to `super().__init__()`
- **D-06:** File name `players/mtt_bot.py` per engine requirements (SAFE-09)
- **D-07:** Detect new hand by checking `len(board_cards) == 0` combined with tracking last-seen board length to detect transitions
- **D-08:** Additive pot tracking -- on each get_action call, read pot_size from game_state (current-street bets); on new street (board length increased), add previous street's final pot_size to running total
- **D-09:** Reset pot accumulator and all per-hand state when new hand detected
- **D-10:** Single file organized with comment banner sections: `# === CONSTANTS ===`, `# === PRECOMPUTATION ===`, `# === HELPERS ===`, `# === BOT CLASS ===`. Module-level code first, class definition last.
- **D-11:** Instance attributes use underscore prefix convention: `self._pot_total`, `self._hand_num`, `self._preflop_aggressor`, etc.
- **D-12:** Helper functions (guard, pot tracking, hand detection) are methods on the class, not module-level functions. Keeps state access simple via `self.*`.

### Claude's Discretion
- Exact premium hand detection logic (how to identify AA/KK/QQ from treys integer cards)
- Guard function internals (validation order, edge case handling)
- Exact section ordering within comment banners
- Error message formatting in try/except fallback

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SAFE-01 | Bot is a class inheriting from `Bot` using `from engine.player_interface import Bot` | Engine bot loading pattern verified in `main.py` lines 59-62 -- uses `inspect.getmembers` + `issubclass(obj, Bot)` |
| SAFE-02 | `get_action()` wraps `_decide()` in try/except with check/fold fallback | Engine already catches exceptions at table.py lines 152-154 and defaults to fold, but our own wrapper gives better control and logging |
| SAFE-03 | Bot never folds when `call_amount == 0` (always checks instead) | Engine behavior verified: fold with call_amount=0 falls through to default check (harmless but wasteful). Guard should prevent this proactively. |
| SAFE-04 | Bot never returns `('check', 0)` -- always uses `('call', 0)` for checks | CRITICAL: Engine table.py lines 181-187 -- `('check', 0)` is unrecognized action. When `call_amount > 0`, engine FOLDS you silently. |
| SAFE-05 | All raise amounts capped at `stack_size` and floored to `min_raise` | Engine floors to min_raise at table.py line 163-164, and player_state.bet() caps at stack. But guard should enforce pre-submission for predictability. |
| SAFE-06 | All instance state is picklable (basic Python types only) | `ProcessPoolExecutor` in main.py line 104 pickles bot for worker process. Only use int/float/str/list/dict/tuple/bool/None. |
| SAFE-07 | `_guard()` function validates every return action before it leaves `_decide()` | Research defines exact validation sequence below in Architecture Patterns |
| SAFE-08 | No blocked imports (only math, random, numpy, pandas, engine.player_interface) | AST scanner in main.py lines 36-49 checks at module level before loading. Includes base module extraction. |
| SAFE-09 | Single file `players/mtt_bot.py` with exactly one Bot subclass | main.py iterates `os.listdir(players_dir)` and loads all .py files. Multiple Bot subclasses in one file would create multiple bots. |
| STATE-01 | Pot accumulator tracks total pot across streets | `pot_size` in game_state is current-street bets only (confirmed via table.py line 137 + line 211 reset). Need additive tracking. |
| STATE-02 | Hand boundary detection resets per-hand state when new hand begins | New hand detection via board_cards length transition, confirmed by table.py's hand lifecycle. |
| STATE-03 | Preflop aggressor flag persists across streets within a hand | Flag set during preflop decision, read during postflop. Must survive street transitions but reset per hand. |
| STATE-04 | Hand counter increments across hands within a simulation | Simple integer incremented on hand boundary detection. Persists across hands, resets per simulation via `__init__`. |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `engine.player_interface` | Engine-provided | `Bot` base class import | Required by engine -- only way to register a bot [VERIFIED: main.py AST scanner] |
| `math` | stdlib | Not needed in Phase 1, but available | Allowed by engine, reserved for future phases |
| `random` | stdlib | Not needed in Phase 1 | Allowed by engine, reserved for MC in Phase 3 |

### Not Using (Phase 1)
| Library | Reason |
|---------|--------|
| `numpy` | No precomputation tables needed yet. Phase 2+ only. [VERIFIED: CLAUDE.md] |
| `pandas` | Zero value for this project. [VERIFIED: CLAUDE.md] |
| `itertools` | BLOCKED by AST scanner. [VERIFIED: main.py ALLOWED_MODULES set] |
| `collections` | BLOCKED by AST scanner. [VERIFIED: main.py ALLOWED_MODULES set] |
| `time` | BLOCKED by AST scanner. [VERIFIED: main.py ALLOWED_MODULES set] |

**Installation:**
```bash
# No installation needed. Single file: players/mtt_bot.py
# Engine provides all dependencies.
```

## Architecture Patterns

### File Structure (from D-10)
```
players/
  mtt_bot.py
    # === CONSTANTS ===
    #   (none in Phase 1, placeholder for Phase 2+ lookup tables)
    # === PRECOMPUTATION ===
    #   (none in Phase 1, placeholder for Phase 2+ module-level builds)
    # === HELPERS ===
    #   (none in Phase 1 -- all helpers are class methods per D-12)
    # === BOT CLASS ===
    #   class HawkEyeBot(Bot):
    #     __init__()
    #     get_action()      -- try/except wrapper
    #     _decide()          -- decision logic
    #     _guard()           -- action validation
    #     _detect_new_hand() -- hand boundary detection
    #     _update_pot()      -- pot accumulator
    #     _is_premium()      -- AA/KK/QQ detection (D-02)
```

### Pattern 1: game_state Dictionary Shape
**What:** The exact dict the engine passes to `get_action()`, verified by reading `table.py` lines 134-143.
**When to use:** Every call to `get_action()`.
```python
# Source: table.py lines 134-143 [VERIFIED: engine source]
state = {
    "hole_cards": [int, int],           # treys integer encoding
    "board_cards": [int, ...],          # 0 (preflop), 3 (flop), 4 (turn), 5 (river)
    "pot_size": int,                    # BROKEN: current-street bets only (see STATE-01)
    "stack_size": int,                  # bot's remaining stack
    "call_amount": int,                 # 0 if can check, >0 if facing bet
    "min_raise": int,                   # minimum raise amount (initialized to big blind)
    "blinds": {"small": int, "big": int},
    "active_players": int               # count of players still in the hand
    # NOTE: "position" is NOT included despite docstring claiming it is
}
```

### Pattern 2: Action Return Tuple Format
**What:** The tuple format the engine expects from `get_action()`.
**When to use:** Every return from `get_action()` and `_decide()`.
```python
# Source: table.py lines 156-188 [VERIFIED: engine source]
# VALID actions the engine recognizes:
("fold", 0)      # fold (only when call_amount > 0)
("call", 0)      # call OR check (engine deduces amount from call_amount)
("raise", amount) # raise by `amount` ON TOP of call_amount
                  # engine does: total_to_put_in = call_amount + amount
                  # engine floors: if amount < min_raise, amount = min_raise
                  # player_state.bet() caps at stack

# DANGEROUS -- engine does NOT recognize these:
# ("check", 0)  --> falls through to default handler
#                   if call_amount > 0: FOLDS YOU SILENTLY
#                   if call_amount == 0: checks (accidental success)
```

### Pattern 3: Guard Function Validation Sequence (SAFE-07)
**What:** The `_guard()` method validates and corrects any action before returning.
**When to use:** Last step in `_decide()`, before returning action tuple.
```python
# Recommended validation order [ASSUMED -- Claude's Discretion per CONTEXT.md]:
def _guard(self, action, amount, game_state):
    call_amount = game_state["call_amount"]
    stack_size = game_state["stack_size"]
    min_raise = game_state["min_raise"]

    # 1. SAFE-04: Never return ('check', 0) -- convert to ('call', 0)
    if action == "check":
        return ("call", 0)

    # 2. SAFE-03: Never fold when call_amount is 0
    if action == "fold" and call_amount == 0:
        return ("call", 0)

    # 3. Handle fold normally
    if action == "fold":
        return ("fold", 0)

    # 4. Handle call
    if action == "call":
        return ("call", 0)

    # 5. SAFE-05: Validate raise amount
    if action == "raise":
        if amount is None or amount < min_raise:
            amount = min_raise
        if amount > stack_size:
            amount = stack_size
        # If we can't afford even min_raise above call, just call
        if stack_size <= call_amount:
            return ("call", 0)
        return ("raise", amount)

    # 6. Fallback: unrecognized action -> call (safe default)
    return ("call", 0)
```

### Pattern 4: Pot Accumulator (STATE-01, D-07, D-08, D-09)
**What:** Tracks total pot across streets since engine's `pot_size` only reflects current-street bets.
**When to use:** Every `_decide()` call, before making decisions.
```python
# Source: table.py line 137 [VERIFIED: engine source]
# pot_size = sum(p.current_bet for p in self.players) + pot_manager.get_total_amount()
# BUT pot_manager.get_total_amount() is 0 during play (collect_bets at showdown only)
# AND current_bet resets to 0 at end of each betting round (line 211)
#
# So pot_size only shows current-round bets. Our accumulator fixes this.

def _update_pot(self, game_state):
    board_len = len(game_state["board_cards"])

    # Detect new hand (D-07)
    if board_len == 0 and self._last_board_len > 0:
        # Board went from >0 back to 0 = new hand
        self._pot_total = 0
        self._street_pot = 0
        # ... reset other per-hand state (D-09)

    # Detect new street (board_len increased from last call)
    if board_len > self._last_board_len:
        # Previous street's bets are now locked in
        self._pot_total += self._street_pot
        self._street_pot = 0

    # Current street's running total from engine
    self._street_pot = game_state["pot_size"]
    self._last_board_len = board_len

    # Estimated total pot = locked streets + current street
    return self._pot_total + self._street_pot
```

### Pattern 5: Premium Hand Detection (D-02, Claude's Discretion)
**What:** Detect AA, KK, QQ from treys integer card encoding.
**When to use:** Preflop decision in `_decide()`.
```python
# Treys integer encoding (from CLAUDE.md):
# rank = ((card >> 8) & 0xF) + 2
# So: A=14, K=13, Q=12, J=11, T=10, ..., 2=2

def _is_premium(self, hole_cards):
    r1 = ((hole_cards[0] >> 8) & 0xF) + 2
    r2 = ((hole_cards[1] >> 8) & 0xF) + 2
    # AA=14,14  KK=13,13  QQ=12,12
    return r1 == r2 and r1 >= 12
```

### Pattern 6: try/except Wrapper (SAFE-02)
**What:** `get_action()` wraps `_decide()` so no exception ever escapes.
**When to use:** The public entry point.
```python
# Source: table.py lines 145-154 [VERIFIED: engine source]
# Engine ALREADY catches exceptions and defaults to fold.
# But our own wrapper lets us return ('call', 0) instead of ('fold', 0),
# which is strictly better when call_amount is 0 (free check vs. fold).

def get_action(self, game_state):
    try:
        return self._decide(game_state)
    except Exception:
        # Safe fallback: call is always legal (checks if 0, calls if >0)
        # Folding on exception wastes free checks
        if game_state.get("call_amount", 0) == 0:
            return ("call", 0)
        return ("fold", 0)
```

### Pattern 7: Bot Lifecycle (Pickling and Instantiation)
**What:** How the engine creates and runs bot instances across simulations.
**When to use:** Understanding `__init__` scope and pickling constraints (SAFE-06).
```python
# Source: main.py lines 59-62, 104-105 [VERIFIED: engine source]
#
# For each simulation:
#   1. main.py calls load_bots() which imports the module fresh
#   2. Finds Bot subclasses via inspect, calls obj() (no-arg constructor)
#   3. Passes bot list to ProcessPoolExecutor.submit()
#   4. Bot is pickled for transfer to worker process
#   5. Tournament creates PlayerState(bot, starting_stack)
#   6. Bot.get_action() called many times during tournament
#
# Implications:
#   - __init__ runs ONCE per simulation (10 times total)
#   - All self.* must be picklable (SAFE-06)
#   - Module-level code runs once per load_bots() call (also 10 times due to importlib)
#   - Module-level constants are fine but not truly "free" -- they rebuild each sim
```

### Anti-Patterns to Avoid
- **Returning `('check', 0)`:** Engine does NOT recognize 'check' as an action type. Falls through to default handler which FOLDS when call_amount > 0. Always use `('call', 0)` for checking. [VERIFIED: table.py lines 156-188]
- **Folding when call_amount is 0:** Wastes a free look. Guard must intercept. [VERIFIED: table.py line 156 -- engine requires call_amount > 0 for fold to trigger]
- **Storing non-picklable objects as instance state:** ProcessPoolExecutor pickles bots. No lambdas, file handles, numpy arrays, or locks. [VERIFIED: main.py line 104]
- **Relying on `game_state["position"]`:** The key does NOT exist in the actual game_state dict built by table.py despite being mentioned in player_interface.py docstring. [VERIFIED: table.py lines 134-143 -- no "position" key]
- **Relying on `game_state["pot_size"]` for total pot:** Only shows current-street bets. [VERIFIED: table.py line 137 + line 211]
- **Raising when stack <= call_amount:** Means we're all-in just to call. Guard must convert to call. [VERIFIED: player_state.py bet() caps at stack]
- **Building lookup tables in `__init__`:** They rebuild every simulation. Module-level is better. (Not relevant for Phase 1 which has no tables, but sets the pattern.) [VERIFIED: CLAUDE.md]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Action validation | Scattered if/else checks in _decide() | Centralized `_guard()` method | Single point of validation prevents any illegal action from escaping. Every code path returns through guard. |
| Exception handling | Per-method try/except | Single wrapper in `get_action()` | Guarantees no exception ever reaches the engine regardless of internal bugs |
| Pot tracking | Reading pot_size directly | `_update_pot()` accumulator method | Engine's pot_size is broken (current-street only). Accumulator is the only reliable total. |

## Common Pitfalls

### Pitfall 1: The ('check', 0) Death Trap
**What goes wrong:** Bot returns `('check', 0)` when facing a bet, engine silently folds.
**Why it happens:** `player_interface.py` docstring does not list valid action strings. The word "check" seems natural. But `table.py` only recognizes "fold", "call", "raise" as action strings.
**How to avoid:** Never use the string "check" anywhere in the codebase. The `_guard()` function catches it, but code should never generate it in the first place. Use `('call', 0)` for both checks and calls.
**Warning signs:** Bot folds an unusual number of hands, especially ones where it should have checked.
[VERIFIED: table.py lines 156-188]

### Pitfall 2: pot_size Lies to You
**What goes wrong:** Bot makes pot-odds calculations using `game_state["pot_size"]` and gets wildly wrong answers after the flop.
**Why it happens:** `pot_size` is calculated as `sum(p.current_bet for p in self.players) + pot_manager.get_total_amount()`. But `current_bet` resets to 0 at end of each betting round (line 211), and `pot_manager.collect_bets()` only runs at showdown (line 214). So during the turn, `pot_size` only reflects turn bets -- all preflop and flop money is invisible.
**How to avoid:** Build the pot accumulator (STATE-01). Never use raw `pot_size` for decisions.
**Warning signs:** Pot size appears to shrink between streets.
[VERIFIED: table.py lines 137, 211, 214]

### Pitfall 3: The First-Hand Detection Edge Case
**What goes wrong:** Bot fails to detect the very first hand of a simulation because `_last_board_len` starts at 0 and the first hand also starts with `board_cards = []` (length 0).
**Why it happens:** The "new hand" signal is "board_len dropped from >0 to 0". On the very first call, both old and new board_len are 0 -- no transition detected.
**How to avoid:** Initialize `_last_board_len` to -1 (sentinel), so the first call with `board_len == 0` triggers hand boundary logic via a different path (e.g., `if self._last_board_len == -1`). Or initialize `_hand_num` to 0 and handle the first call as implicit first hand.
**Warning signs:** Hand counter shows 0 when it should show 1. Per-hand state is never initialized for the first hand.
[ASSUMED -- edge case analysis]

### Pitfall 4: Module-Level Code Runs Per Simulation
**What goes wrong:** Developer assumes module-level code runs once total and puts expensive computation there.
**Why it happens:** `main.py` line 105 calls `load_bots()` inside the ProcessPoolExecutor dict comprehension. Each call does `importlib.import_module()` which re-executes the module.
**How to avoid:** Module-level code is still the right place for constants and precomputation (vs. `__init__`), since it only runs once per simulation. Just be aware it's 10 times total, not 1. For Phase 1 this is irrelevant (no precomputation), but important to know for Phase 2+.
**Warning signs:** None immediate -- it's a performance concern, not a crash risk.
[VERIFIED: main.py lines 104-105]

### Pitfall 5: Raise Amount Semantics
**What goes wrong:** Bot returns `('raise', total_bet)` thinking amount is the total. Engine treats it as raise ON TOP of call_amount.
**Why it happens:** Ambiguity in whether "raise amount" means total bet or additional raise.
**How to avoid:** The engine does `total_to_put_in = call_amount + amount` (table.py line 165). So `amount` in the return tuple is the additional raise. If you want to bet 100 total and call_amount is 30, return `('raise', 70)`. Guard should enforce `amount >= min_raise` and `amount <= stack_size` (the raise portion, not total).
**Warning signs:** Bot raises much more than intended, or raises are rejected/floored to min.
[VERIFIED: table.py lines 164-165]

### Pitfall 6: Heads-Up Blind Posting Quirk
**What goes wrong:** Bot assumes standard heads-up rules (button posts SB, other posts BB) but engine has button posting BB.
**Why it happens:** table.py lines 54-55: `bb_idx = self.button_idx` when `num_players == 2`.
**How to avoid:** Don't rely on position for Phase 1 (position isn't even in game_state). But be aware for future phases: in heads-up, the non-button player is SB and acts first postflop, while button is BB.
**Warning signs:** Incorrect position inference in heads-up scenarios.
[VERIFIED: table.py lines 54-55]

### Pitfall 7: game_state["position"] Does Not Exist
**What goes wrong:** Bot tries to access `game_state["position"]` and crashes with KeyError.
**Why it happens:** `player_interface.py` docstring says `"position"` is in the dict. But `table.py` lines 134-143 simply don't include it. The docstring is aspirational, not implemented.
**How to avoid:** Never access `game_state["position"]`. Use `.get("position", None)` at most, but don't rely on it.
**Warning signs:** Immediate KeyError crash on first hand.
[VERIFIED: table.py lines 134-143 vs player_interface.py docstring]

## Code Examples

### Complete Bot Skeleton Structure
```python
# Source: Synthesis of all engine source analysis [VERIFIED: engine source files]
from engine.player_interface import Bot

class HawkEyeBot(Bot):
    def __init__(self):
        super().__init__("HawkEye")
        # Per-simulation state (persists across hands)
        self._hand_num = 0           # STATE-04
        # Per-hand state (reset each hand)
        self._last_board_len = -1    # Sentinel for first-hand detection
        self._pot_total = 0          # STATE-01: accumulated pot from prior streets
        self._street_pot = 0         # STATE-01: current street pot
        self._was_preflop_aggressor = False  # STATE-03

    def get_action(self, game_state):
        # SAFE-02: try/except wrapper
        try:
            return self._decide(game_state)
        except Exception:
            if game_state.get("call_amount", 0) == 0:
                return ("call", 0)
            return ("fold", 0)

    def _decide(self, game_state):
        # 1. Detect hand boundary, update pot
        # 2. Make decision
        # 3. Pass through _guard() before returning
        ...
        return self._guard(action, amount, game_state)

    def _guard(self, action, amount, game_state):
        # SAFE-03, SAFE-04, SAFE-05, SAFE-07
        ...

    def _detect_new_hand(self, game_state):
        # STATE-02, STATE-04
        ...

    def _update_pot(self, game_state):
        # STATE-01
        ...

    def _is_premium(self, hole_cards):
        # D-02: AA/KK/QQ detection
        ...
```

### Minimal Working Example (CallBot Pattern)
```python
# Source: players/call_bot.py [VERIFIED: engine source]
from engine.player_interface import Bot

class CallBot(Bot):
    def __init__(self):
        super().__init__("CallBot")

    def get_action(self, game_state):
        return ('call', 0)
```
This is the absolute minimum. Phase 1 builds on this pattern with safety guards and state tracking.

### Engine Action Handling -- Complete Flow
```python
# Source: table.py lines 156-188 [VERIFIED: engine source]
# This is what the engine does with our return tuple:

if action == "fold" and call_amount > 0:
    # Fold -- player marked inactive
    player.is_active = False

elif action == "call":
    # Call -- engine deducts call_amount from stack
    actual_bet = player.bet(call_amount)

elif action == "raise":
    # Raise -- engine floors amount to min_raise if too small
    if amount is None or amount < min_raise:
        amount = min_raise
    total_to_put_in = call_amount + amount
    actual_bet = player.bet(total_to_put_in)  # capped at stack

else:
    # DEFAULT: unrecognized action (including 'check')
    if call_amount > 0:
        player.is_active = False  # FOLD!
    # else: check (no action needed)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Rely on engine pot_size | Accumulate pot manually | Required from Phase 1 | Correct pot odds calculations in all later phases |
| Use ('check', 0) for checks | Always use ('call', 0) | Required from Phase 1 | Prevents silent folds |
| Trust player_interface.py docs | Read table.py source | Research finding | position key missing, action semantics differ from docs |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | First-hand edge case: initializing `_last_board_len` to -1 as sentinel handles the first call correctly | Pitfall 3, Architecture Pattern 4 | Minor -- would miss first hand state initialization, but bot still works; worst case is first hand pot tracking is off |
| A2 | Treys integer encoding rank extraction formula `((card >> 8) & 0xF) + 2` gives Ace=14, King=13, Queen=12 | Pattern 5 | HIGH -- if formula is wrong, premium hand detection fails. Formula from CLAUDE.md project research, should be verified against actual engine card values. |
| A3 | `importlib.import_module` re-executes module-level code on each call in the ProcessPoolExecutor context | Pitfall 4 | LOW -- even if cached, module-level code is still fast and correct for Phase 1 |

## Open Questions

1. **Treys integer encoding verification**
   - What we know: CLAUDE.md states `rank = ((card >> 8) & 0xF) + 2` for treys cards. The engine uses `treys.Deck` and `treys.Card`.
   - What's unclear: Whether the actual treys library installed with the engine uses exactly this bit layout. The treys library documentation confirms this format, but the engine's specific version is unknown.
   - Recommendation: For Phase 1, this only affects `_is_premium()` (AA/KK/QQ detection). If the formula is wrong, the bot still works -- it just won't raise with premiums. Low risk. Can verify by printing card values in a test run.

2. **How many bots compete in the actual tournament?**
   - What we know: Config has `max_players_per_table: 9`. Tournament supports multi-table.
   - What's unclear: How many student submissions there will be. This affects tournament stage timing.
   - Recommendation: Not relevant for Phase 1. Becomes relevant in Phase 5 (tournament awareness).

3. **Does the engine send game_state calls when bot is all-in?**
   - What we know: table.py line 129 checks `if player.is_active and not player.is_all_in` before calling get_action. So all-in players are NOT asked for actions.
   - What's unclear: Nothing -- this is verified.
   - Recommendation: Confirmed: no game_state calls when all-in. Pot accumulator may miss bets from rounds where we went all-in early. Acceptable for Phase 1.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Manual testing against engine |
| Config file | None -- run against MTT engine directly |
| Quick run command | `python main.py` (from engine directory with bot in players/) |
| Full suite command | `python main.py` (runs 10 simulations per config) |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SAFE-01 | Bot loads in engine | smoke | `python main.py` -- bot appears in "Loaded N player bots" | No -- Wave 0 |
| SAFE-02 | Exception in _decide() caught | unit | Temporarily inject `raise Exception` in _decide, verify no crash | No -- Wave 0 |
| SAFE-03 | Never fold when call_amount=0 | manual/review | Code review of _guard() + grep for "fold" returns | No -- Wave 0 |
| SAFE-04 | Never return ('check', 0) | manual/review | Code review of _guard() + grep for "'check'" | No -- Wave 0 |
| SAFE-05 | Raise amounts bounded | manual/review | Code review of _guard() raise validation | No -- Wave 0 |
| SAFE-06 | All state picklable | smoke | Bot completes 10 sims (ProcessPoolExecutor would fail on unpicklable) | No -- Wave 0 |
| SAFE-07 | _guard() validates all returns | unit | Test _guard() with edge case inputs | No -- Wave 0 |
| SAFE-08 | No blocked imports | smoke | Engine loads bot (AST scanner passes) | No -- Wave 0 |
| SAFE-09 | Single file, one Bot subclass | manual/review | File structure verification | No -- Wave 0 |
| STATE-01 | Pot accumulator across streets | unit | Simulate multi-street game_state sequence, verify totals | No -- Wave 0 |
| STATE-02 | Hand boundary resets state | unit | Simulate hand transition game_state sequence | No -- Wave 0 |
| STATE-03 | Preflop aggressor persists | unit | Set flag preflop, verify present on flop call | No -- Wave 0 |
| STATE-04 | Hand counter increments | unit | Simulate multiple hand transitions, verify count | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** Run bot through engine -- verify no crash
- **Per wave merge:** Full 10-simulation run
- **Phase gate:** 10 simulations complete with zero crashes, timeouts, or engine error messages

### Wave 0 Gaps
- [ ] `players/` directory does not exist yet -- must create
- [ ] No test infrastructure exists -- primary validation is running against the engine
- [ ] Consider a lightweight test script that feeds synthetic game_state dicts to bot.get_action() for unit-level validation of guard/pot/hand detection

## Security Domain

Security enforcement is not applicable to this project. The bot is a single-player script running in a controlled tournament engine. No user input, no network, no authentication, no data storage.

## Sources

### Primary (HIGH confidence)
- `Docs/MTT-Pokerbot-Engine/engine/table.py` -- Betting round logic, pot_size calculation, action handling, heads-up blinds
- `Docs/MTT-Pokerbot-Engine/engine/player_interface.py` -- Bot base class, get_action signature, game_state docstring
- `Docs/MTT-Pokerbot-Engine/engine/player_state.py` -- Player state management, bet() capping, setup_new_hand()
- `Docs/MTT-Pokerbot-Engine/engine/pot.py` -- PotManager, collect_bets() at showdown only
- `Docs/MTT-Pokerbot-Engine/engine/config.py` -- Config loading, timeout, blind schedule
- `Docs/MTT-Pokerbot-Engine/engine/tournament.py` -- Tournament lifecycle, play() loop
- `Docs/MTT-Pokerbot-Engine/main.py` -- Bot loading (AST scanner, ProcessPoolExecutor), ALLOWED_MODULES
- `Docs/MTT-Pokerbot-Engine/config.json` -- 500ms timeout, 1500 starting stack, blind schedule
- `Docs/MTT-Pokerbot-Engine/players/call_bot.py` -- Minimal bot pattern
- `Docs/MTT-Pokerbot-Engine/players/random_bot.py` -- Bot with raise logic

### Secondary (MEDIUM confidence)
- `CLAUDE.md` project instructions -- Treys card encoding, algorithm stack, constraints

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- Only uses engine-provided interfaces, no external libraries needed for Phase 1
- Architecture: HIGH -- All patterns derived from direct reading of engine source code
- Pitfalls: HIGH -- Every pitfall verified against actual engine source except first-hand edge case (A1) which is logic analysis
- State tracking: HIGH -- pot_size bug and current_bet reset confirmed line-by-line in table.py

**Research date:** 2026-04-10
**Valid until:** 2026-04-23 (tournament deadline -- engine source will not change)
