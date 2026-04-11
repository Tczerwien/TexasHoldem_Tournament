# Architecture Patterns

**Domain:** Single-file MTT poker bot (Python, tournament engine)
**Researched:** 2026-04-10

## Recommended Architecture

A layered pipeline within a single file, organized by execution phase: precomputation (module-level, free of 500ms budget) then runtime decision pipeline (per-call, within 500ms). The bot is a single class with module-level helper functions and lookup tables.

### Single-File Organization (top to bottom)

```
mtt_bot.py
  |
  |-- [1] IMPORTS (3 lines: engine.player_interface, math, random)
  |
  |-- [2] CONSTANTS (~60 lines: all numeric thresholds, no magic numbers)
  |
  |-- [3] PRECOMPUTATION FUNCTIONS + TABLES (~150 lines)
  |     |-- _build_full_deck() -> FULL_DECK (52 treys ints)
  |     |-- _build_chen_table() -> CHEN_TABLE (169 entries)
  |     |-- _build_shove_table() -> SHOVE_TABLE (~100 entries)
  |     |-- _build_call_table() -> CALL_TABLE (~60 entries)
  |
  |-- [4] CARD UTILITIES (~30 lines)
  |     |-- get_rank(), get_suit(), _decode_hand()
  |
  |-- [5] CONTEXT HELPERS (~30 lines)
  |     |-- _get_stack_mode(), _get_stage(), _get_stack_role()
  |
  |-- [6] SIZING HELPERS (~30 lines)
  |     |-- _calc_open_size(), raise_to(), safe_raise(), _make_bet()
  |
  |-- [7] PUSH-FOLD HELPERS (~15 lines)
  |     |-- should_shove_open(), should_call_shove()
  |
  |-- [8] EVALUATION ENGINE (~120 lines)
  |     |-- _eval_7cards() -- 7-card hand evaluator (C(7,5) combos)
  |     |-- _mc_equity() -- Monte Carlo simulation loop
  |     |-- _detect_draws() -- flush/OESD/gutshot detection
  |     |-- _effective_hand_strength() -- EHS = MC equity + draw bonus
  |     |-- _classify_board_texture() -- DRY/SEMI_WET/WET/PAIRED
  |
  |-- [9] SAFETY GUARD (~20 lines)
  |     |-- _guard() -- enforces all safety invariants
  |
  |-- [10] BOT CLASS (~200 lines)
        |-- __init__() -- instance state (pot accumulator, hand tracking)
        |-- get_action() -- try/except entry point
        |-- _decide() -- main router
        |-- _is_new_hand(), _reset_hand_state()
        |-- _update_pot_accumulator(), _get_estimated_pot()
        |-- _preflop() -> _preflop_full / _preflop_shallow / _preflop_push_fold
        |-- _postflop() -> _postflop_check_or_bet / _postflop_facing_bet
```

**Estimated total:** ~650-750 lines.

### Why This Ordering

1. **Constants before functions** -- functions reference constants; no forward declarations needed.
2. **Precomputation at module top** -- tables are built once at import time (verified: runs before 500ms clock starts). Functions that build tables must precede the `TABLE = _build_table()` assignment lines.
3. **Stateless helpers before class** -- the class calls module-level functions. Python requires definition before use at module scope (the class body references these via method calls, which is fine at call time, but the module-level table assignments must be after their builder functions).
4. **Class at bottom** -- single Bot subclass. Engine scans for Bot subclasses via `inspect.getmembers`; only one class should inherit from Bot (multiple would register as separate players).

### Component Boundaries

| Component | Responsibility | Communicates With | State? |
|-----------|---------------|-------------------|--------|
| **Constants** | All numeric thresholds | Referenced by all components | No (immutable) |
| **Precomputed Tables** | Chen scores, push-fold ranges, deck | Queried by Preflop Pipeline, Push-Fold | No (immutable after build) |
| **Card Utilities** | Decode treys integers to rank/suit | Used by all evaluation + preflop logic | No |
| **Context Helpers** | Stack mode, tournament stage, stack role | Called by `_decide()`, passed to pipelines | No |
| **Sizing Helpers** | Construct legal raise/bet actions | Called by preflop + postflop pipelines | No |
| **Evaluation Engine** | Hand strength, equity, draws, board texture | Called by postflop pipeline | No |
| **Safety Guard** | Enforce action legality invariants | Wraps every action returned by `_decide()` | No |
| **Bot Class (state)** | Pot accumulation, hand boundary detection, aggressor tracking | Owns instance state; delegates to all helpers | Yes (picklable) |
| **Bot Class (preflop)** | Preflop decision tree | Reads tables + context; returns action | No (uses class state read-only) |
| **Bot Class (postflop)** | Postflop decision tree | Calls evaluation engine; reads pot accumulator | No (uses class state read-only) |

### Data Flow

```
Engine calls get_action(game_state)
        |
        v
  [try/except wrapper]
        |
        v
  _decide(game_state)
        |
        |-- _is_new_hand() --> _reset_hand_state()  (hand boundary)
        |-- _update_pot_accumulator()                (pot tracking)
        |-- _get_stack_mode()                        (context)
        |-- _get_stage()                             (context)
        |-- _decode_hand()                           (card decode)
        |
        |-- if PREFLOP:
        |     |-- stack_mode == 'push_fold'?
        |     |     --> SHOVE_TABLE / CALL_TABLE lookup --> action
        |     |-- stack_mode == 'shallow'?
        |     |     --> CHEN_TABLE lookup + shove logic --> action
        |     |-- stack_mode in ('medium','deep')?
        |           --> CHEN_TABLE lookup
        |           --> situation classify (BB opt / SB / RFI / facing raise / facing 3bet)
        |           --> _calc_open_size() / raise_to() --> action
        |
        |-- if POSTFLOP:
              |-- _get_estimated_pot()                (pot workaround)
              |-- _effective_hand_strength()
              |     |-- _mc_equity()
              |     |     |-- random.sample(deck)     (deal opponents + runout)
              |     |     |-- _eval_7cards()           (evaluate all hands, 21 combos each)
              |     |     |-- compare ranks            (win/loss/tie)
              |     |-- _detect_draws()               (flush/OESD/gutshot)
              |     |-- combine: EHS = raw_eq + bonus * (1 - raw_eq)
              |-- _classify_board_texture()
              |-- call_amount == 0?
              |     --> _postflop_check_or_bet()       (c-bet / value bet / check)
              |-- call_amount > 0?
                    --> _postflop_facing_bet()          (pot odds / ICM / raise / call / fold)
        |
        v
  _guard(action, game_state)  <-- enforces never-fold-free, no 'check', cap raise
        |
        v
  return (action, amount)  --> Engine
```

### Critical Data Flow: Pot Accumulation

The `pot_size` field from the engine only contains current-street bets. This is the single most important architectural consideration.

```
Hand starts:
  _street_pot_base = 0
  _last_street = 0
  _last_pot_size = 0

Preflop call 1:  pot_size=30 (blinds in)  -> _last_pot_size = 30
Preflop call 2:  pot_size=60 (we raised)  -> _last_pot_size = 60

Flop call:
  board_len=3, _last_street=0 -> STREET CHANGE
  _street_pot_base += _last_pot_size (60)  -> _street_pot_base = 60
  pot_size=20 (someone bet)
  estimated_total = 60 + 20 = 80   <-- correct approximation

Turn call:
  board_len=4, _last_street=3 -> STREET CHANGE
  _street_pot_base += _last_pot_size (prev flop pot_size)
  ... continues accumulating
```

**Known limitation:** Bets made by opponents AFTER our last action on a street are lost. The error is bounded by one opponent bet and acceptable for v1.

### Instance State (Must Be Picklable)

All instance state is plain Python primitives. The engine pickles bots for `ProcessPoolExecutor`.

| Attribute | Type | Purpose | Reset |
|-----------|------|---------|-------|
| `_street_pot_base` | `int` | Accumulated pot from prior streets | Per hand |
| `_last_street` | `int` | Last seen `len(board_cards)` | Per hand |
| `_last_pot_size` | `int` | Last seen `pot_size` value | Per hand |
| `_was_preflop_aggressor` | `bool` | Did we raise preflop? (drives c-bet) | Per hand |
| `_hand_count` | `int` | Hands played (monotonic) | Never (increments) |

Total instance state: 5 attributes, all ints/bools. Trivially picklable.

## Patterns to Follow

### Pattern 1: Precomputation Over Runtime Calculation

**What:** Move all deterministic computation to module-level (import time). This includes the Chen score table (169 entries), push-fold shove ranges, push-fold call ranges, and the full deck.

**When:** Any lookup that does not depend on runtime game_state.

**Why:** Module-level code runs once at import, completely outside the 500ms-per-decision budget. A dict lookup is O(1) vs. recomputing Chen formula (~20 operations) on every hand.

```python
# At module level (runs once, free):
CHEN_TABLE = _build_chen_table()  # 169 entries

# At runtime (O(1)):
chen = CHEN_TABLE[(rank_hi, rank_lo, suited)]
```

### Pattern 2: Decision Tree With Early Exit

**What:** Structure decision logic as a chain of if/return statements, never nested if/else blocks deeper than 2 levels.

**When:** All decision pipelines (preflop, postflop).

**Why:** Single-file readability. Deep nesting in 700 lines makes bugs invisible. Early returns make each branch independently testable.

```python
def _preflop_push_fold(gs, stack_bb, call, bb, sb, stack, r_hi, r_lo, suited):
    if call == 0 or call == sb:
        if should_shove_open(r_hi, r_lo, suited, stack_bb):
            return safe_raise(stack, gs)
        if call == 0:
            return ('call', 0)
        return ('fold', 0)
    
    villain_bb = call / bb
    if should_call_shove(r_hi, r_lo, suited, villain_bb):
        return ('call', 0)
    return ('fold', 0)
```

### Pattern 3: Guard-at-Exit

**What:** Every action flows through `_guard()` before returning to the engine. The guard enforces safety invariants (never fold free, no 'check' string, cap raises).

**When:** Always. Non-negotiable.

**Why:** Engine quirks (Section 9d of ENGINE_INTERFACE) mean returning `('check', 0)` when `call_amount > 0` silently folds you. A single guard function is easier to audit than checking every return site.

### Pattern 4: Module-Level Functions Over Class Methods

**What:** Stateless helper functions (card utilities, context helpers, evaluation) are module-level functions, not class methods.

**When:** Any function that does not read or write `self.*` attributes.

**Why:** 
- Reduces class surface area -- only stateful logic is in the class
- Module-level functions are slightly faster (no `self` argument dispatch)
- Easier to test in isolation
- Only the Bot class can have `self` -- the engine instantiates it via `inspect.getmembers`

## Anti-Patterns to Avoid

### Anti-Pattern 1: Multiple Classes Inheriting Bot

**What:** Defining helper classes that also inherit from Bot (e.g., `class PreflopBot(Bot)`).

**Why bad:** The engine scans for ALL Bot subclasses and registers each as a separate player. Two Bot subclasses = two entries in the tournament, splitting your code into two competing bots.

**Instead:** One class (`MTTBot`). All other logic in module-level functions.

### Anti-Pattern 2: Using pot_size Directly for Pot Odds

**What:** Computing `req_eq = call / (pot_size + call)` using `game_state['pot_size']`.

**Why bad:** `pot_size` only contains current-street bets. On the flop, it starts at 0 regardless of preflop action. Your pot odds calculation will be wildly wrong (infinite required equity when pot appears to be 0).

**Instead:** Use `_get_estimated_pot()` which adds the pot accumulator.

### Anti-Pattern 3: Importing Blocked Libraries

**What:** Using `import collections`, `from itertools import combinations`, `import time`, etc.

**Why bad:** The engine AST-scans imports before loading. Any blocked import disqualifies the bot for all 10 simulations. Zero score.

**Instead:** Implement `combinations(cards, 5)` manually (21 combos from 7 cards). Use `random.sample()` instead of `itertools`. Use iteration counts instead of `time.time()`.

### Anti-Pattern 4: Non-Picklable Instance State

**What:** Storing lambdas, file handles, numpy arrays, or class instances as `self.*` attributes.

**Why bad:** Engine uses `ProcessPoolExecutor` which pickles bot objects. Non-picklable state causes silent failures.

**Instead:** Only `int`, `float`, `bool`, `str`, `list`, `dict`, `tuple` as instance attributes.

### Anti-Pattern 5: Deep Nesting in Single File

**What:** 4+ levels of nested if/else in a 700-line file.

**Why bad:** Impossible to debug, easy to misplace an `else`. Single-file constraint already makes navigation hard.

**Instead:** Decompose into sub-pipelines (`_preflop_full`, `_preflop_shallow`, `_preflop_push_fold`). Use early return. Keep each function under 40 lines.

## Suggested Build Order (Dependencies)

Build order is dictated by testability -- each phase must produce a bot that loads and plays legally.

```
Phase 1: Skeleton + Safety
  |- Card utilities (get_rank, get_suit, _decode_hand)
  |- Context helpers (_get_stack_mode, _get_stage)
  |- Sizing helpers (safe_raise, raise_to, _make_bet)
  |- Safety guard (_guard)
  |- Bot class shell (get_action -> try/except -> _decide stub)
  |- Pot accumulator (_update_pot_accumulator, _get_estimated_pot)
  |- Hand boundary (_is_new_hand, _reset_hand_state)
  RESULT: Bot loads, plays check/fold, never crashes.

Phase 2: Preflop Engine
  |- FULL_DECK precomputation
  |- CHEN_TABLE precomputation
  |- SHOVE_TABLE + CALL_TABLE precomputation
  |- _preflop() router
  |- _preflop_full() -- 5 situation branches (BB opt, SB, RFI, facing raise, facing 3bet)
  |- _preflop_shallow()
  |- _preflop_push_fold()
  DEPENDS ON: Phase 1 (card utils, context, sizing, guard)
  RESULT: Bot makes correct preflop decisions. Postflop still check/fold.

Phase 3: Postflop Core
  |- _eval_7cards() -- the hardest single function (~100 lines)
  |- _mc_equity() -- MC simulation loop using _eval_7cards
  |- _detect_draws()
  |- _effective_hand_strength() -- combines MC + draw bonus
  |- _classify_board_texture()
  |- _postflop_check_or_bet() -- c-bet logic
  |- _postflop_facing_bet() -- pot odds decisions
  DEPENDS ON: Phase 1 (pot accumulator), Phase 2 (FULL_DECK, aggressor tracking)
  RESULT: Complete playing bot with all streets covered.

Phase 4: Tournament Polish
  |- _get_stack_role() -- bubble stack approximation
  |- ICM integration in postflop facing-bet
  |- Bubble/ITM range adjustments
  |- Heads-up quirk handling
  DEPENDS ON: Phase 3 (postflop pipeline exists to modify)
  RESULT: Tournament-aware bot.

Phase 5: Tuning
  |- MC iteration benchmarking (fit within 250ms)
  |- Exploitation adjustments for weak field
  |- Edge case stress testing
  |- Remove debug code
  DEPENDS ON: Phase 4 (all logic complete)
  RESULT: Submission-ready bot.
```

### Build Order Rationale

1. **Skeleton first** because a bot that crashes is worse than a bot that check/folds. The try/except wrapper and safety guard are survival features.
2. **Preflop before postflop** because preflop decisions are table-lookup based (fast to implement, easy to verify) and the preflop aggressor flag drives postflop c-bet logic.
3. **_eval_7cards before _mc_equity** because MC equity calls the evaluator. The evaluator is the most complex single function (~100 lines, C(7,5)=21 combos, 9 hand categories) and the highest bug risk.
4. **Tournament polish last** because ICM/bubble adjustments are multipliers on top of working logic. They provide marginal EV improvement. A bot without ICM awareness but with correct pot odds beats a bot with ICM but broken equity calculation.

## Performance Budget

| Operation | Budget | Notes |
|-----------|--------|-------|
| Game state parsing + context | 2ms | Dict lookups, arithmetic |
| Preflop lookup | 1ms | CHEN_TABLE / SHOVE_TABLE dict access |
| MC equity (300-500 iters) | 200-250ms | Dominant cost; benchmark locally |
| Draw detection | 1ms | Suit/rank counting |
| Board texture | 1ms | Rank/suit frequency |
| Decision logic | 5ms | Threshold comparisons |
| Safety guard | <1ms | 4 conditionals |
| **Buffer (untouchable)** | **240ms** | Safety margin for slow hardware |

The 7-card evaluator inside each MC iteration is the true bottleneck. Each call evaluates 21 five-card combinations. At 300 iterations with 2 opponents, that is 300 * 3 * 21 = 18,900 five-card evaluations per decision. The evaluator must be tight -- no allocations inside the inner loop where avoidable, use rank frequency arrays rather than sorting.

## Sources

- `Docs/SPEC.md` -- Build specification with complete decision pipelines and function contracts
- `Docs/ENGINE_INTERFACE.md` -- Verified engine interface, quirks, and constraints
- `.planning/PROJECT.md` -- Project context, requirements, and constraints
- Engine source code analysis (referenced in ENGINE_INTERFACE.md): `main.py`, `table.py`, `player_interface.py`
