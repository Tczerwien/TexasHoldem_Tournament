# Requirements: MTTBot

**Defined:** 2026-04-10
**Core Value:** Win the IIT Poker Club MTT tournament by maximizing aggregate points across 10 simulations

## v1 Requirements

Requirements for initial tournament submission (April 23, 2026). Each maps to roadmap phases.

### Safety & Infrastructure

- [ ] **SAFE-01**: Bot is a class inheriting from `Bot` using `from engine.player_interface import Bot`
- [ ] **SAFE-02**: `get_action()` wraps `_decide()` in try/except with check/fold fallback
- [ ] **SAFE-03**: Bot never folds when `call_amount == 0` (always checks instead)
- [ ] **SAFE-04**: Bot never returns `('check', 0)` — always uses `('call', 0)` for checks
- [ ] **SAFE-05**: All raise amounts capped at `stack_size` and floored to `min_raise`
- [ ] **SAFE-06**: All instance state is picklable (basic Python types only, no lambdas/file handles)
- [ ] **SAFE-07**: `_guard()` function validates every return action before it leaves `_decide()`
- [ ] **SAFE-08**: No blocked imports (only math, random, numpy, pandas, engine.player_interface)
- [ ] **SAFE-09**: Single file `players/mtt_bot.py` with exactly one Bot subclass

### State Tracking

- [ ] **STATE-01**: Pot accumulator tracks total pot across streets (workaround for broken `pot_size`)
- [ ] **STATE-02**: Hand boundary detection resets per-hand state when new hand begins
- [ ] **STATE-03**: Preflop aggressor flag (`_was_preflop_aggressor`) persists across streets within a hand
- [ ] **STATE-04**: Hand counter increments across hands within a simulation

### Preflop Core

- [ ] **PRE-01**: Chen formula hand classification with 169-entry precomputed lookup table
- [ ] **PRE-02**: Stack mode detection (deep >= 40BB, medium >= 25BB, shallow >= 15BB, push-fold < 15BB)
- [ ] **PRE-03**: Preflop opening ranges by stack mode (deep ~20%, medium ~15%, shallow reshove-only)
- [ ] **PRE-04**: Push-fold shove table for <15BB with stack-depth-dependent ranges (precomputed)
- [ ] **PRE-05**: Push-fold call table for facing shoves with villain-stack-dependent ranges (precomputed)
- [ ] **PRE-06**: Position inference from `call_amount` relative to blinds (RFI/facing open/facing 3-bet/BB option/SB complete)
- [ ] **PRE-07**: Preflop situational strategy with different hand requirements per situation
- [ ] **PRE-08**: 3-bet logic (QQ+/AKs facing an open) and 4-bet logic (AA/KK facing a 3-bet)
- [ ] **PRE-09**: Preflop raise sizing by stack mode (2.5x/2.2x/2.0x BB or shove)

### Postflop Core

- [ ] **POST-01**: 7-card hand evaluator using only rank/suit extraction (no treys), evaluating all C(7,5)=21 combos
- [ ] **POST-02**: Monte Carlo equity estimation with fixed iteration caps (300 flop / 400 turn / 500 river)
- [ ] **POST-03**: Draw detection (flush draw, OESD, gutshot, combo draw)
- [ ] **POST-04**: Effective Hand Strength (EHS) combining raw MC equity with draw bonus
- [ ] **POST-05**: Board texture classification (DRY / SEMI_WET / WET / PAIRED)
- [ ] **POST-06**: C-bet logic based on preflop aggressor status, EHS bucket, and board texture
- [ ] **POST-07**: Pot odds call/fold decisions using `req_eq = call_amount / (est_pot + call_amount)`
- [ ] **POST-08**: Raise/call/fold facing a bet using EHS vs required equity multipliers
- [ ] **POST-09**: Bet sizing system (33-75% pot by street, texture, and situation)
- [ ] **POST-10**: Stack commitment rule (bet >= 60% of stack -> shove instead)
- [ ] **POST-11**: Turn barreling with STRONG+ hands (66% pot)
- [ ] **POST-12**: River value betting with STRONG+ hands (75% pot)
- [ ] **POST-13**: SPR-based commitment decisions (SPR < 1.5 and betting -> shove)

### Tournament Awareness

- [ ] **TOURN-01**: Tournament stage detection from blind level + active_players (early/middle/late/bubble/ITM/heads-up)
- [ ] **TOURN-02**: ICM calling multiplier at bubble (1.4x required equity for all-in calls)
- [ ] **TOURN-03**: Big/medium/short stack role detection at bubble (approximate from avg stack)
- [ ] **TOURN-04**: Bubble play adjustments (big stack bullies, medium stack tightens, short stack shoves)
- [ ] **TOURN-05**: In-money aggression switch (release ICM pressure when 3 players remain, fight for 1st)
- [ ] **TOURN-06**: Heads-up range widening (55%+ opening range, account for button-posts-BB engine quirk)
- [ ] **TOURN-07**: Exploit adjustments for weak/passive fields (reduce EHS value bet threshold by 0.10)

### Precomputation

- [ ] **COMP-01**: Full 52-card deck built at module level in treys integer encoding
- [ ] **COMP-02**: Chen score table (169 entries) built at module level
- [ ] **COMP-03**: Push-fold shove table built at module level
- [ ] **COMP-04**: Push-fold call table built at module level
- [ ] **COMP-05**: All precomputation runs at import time, free of 500ms per-decision budget

## v2 Requirements

Deferred to post-submission optimization milestone. Tracked but not in v1 roadmap.

### Performance Optimization

- **PERF-01**: Cactus Kev prime-product lookup evaluator (O(1) per 5-card eval via hash tables instead of combinatorial ranking)
- **PERF-02**: River exact enumeration of all C(remaining,2) opponent combos (~990) instead of MC sampling
- **PERF-03**: Adaptive MC iteration count (fewer iterations when EHS is clearly monster/air, more when borderline)
- **PERF-04**: Numpy-vectorized MC batching (evaluate multiple opponent hands in parallel via array operations)
- **PERF-05**: Precomputed flop equity buckets for common hand-category vs board-texture combinations (skip MC for clear spots)

### Strategic Refinement

- **STRAT-01**: Simulation-level opponent profiling (track aggregate raise/fold/call rates across hands within one sim, adjust exploit intensity dynamically)
- **STRAT-02**: Multi-street bluff planning (check-raise bluffs, delayed c-bets, balanced river bluff frequency cap at 1/3 of river bets)
- **STRAT-03**: Dynamic preflop range adjustment based on observed field aggression level within current simulation
- **STRAT-04**: Stack-relative preflop adjustments (widen/tighten ranges based on estimated table chip distribution)

### Edge Polish

- **EDGE-01**: Kicker-aware hand strength differentiation (TPTK vs TP weak kicker in postflop bucket assignment)
- **EDGE-02**: Minimum defense frequency awareness (auto-widen call range if folding too often to prevent exploitation)
- **EDGE-03**: Refined river bluff candidate selection (only bluff missed draws, not random air)
- **EDGE-04**: Heads-up specific postflop adjustments (wider c-bet range, thinner value bets, more frequent bluffs)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Machine learning / neural networks | sklearn, scipy, torch blocked by AST import scanner |
| GTO solver / CFR training | Requires millions of iterations and blocked libraries |
| Opponent modeling from action history | `action_history` absent from game_state |
| Multi-file architecture | Engine requires single .py file in players/ directory |
| Limping preflop | Dominated strategy in tournament poker |
| Slow-playing monsters | Against calling-station field, value betting is strictly superior |
| Time-based logic | `time` module blocked; use fixed iteration counts |
| Position tracking from seat numbers | `position` field absent from game_state |
| Complex multi-street bluff narratives (v1) | Requires opponent reads not available; deferred to v2 |
| Real-time opponent adaptation (v1) | No per-hand action data; sim-level profiling deferred to v2 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SAFE-01 | Phase 1 | Pending |
| SAFE-02 | Phase 1 | Pending |
| SAFE-03 | Phase 1 | Pending |
| SAFE-04 | Phase 1 | Pending |
| SAFE-05 | Phase 1 | Pending |
| SAFE-06 | Phase 1 | Pending |
| SAFE-07 | Phase 1 | Pending |
| SAFE-08 | Phase 1 | Pending |
| SAFE-09 | Phase 1 | Pending |
| STATE-01 | Phase 1 | Pending |
| STATE-02 | Phase 1 | Pending |
| STATE-03 | Phase 1 | Pending |
| STATE-04 | Phase 1 | Pending |
| PRE-01 | Phase 2 | Pending |
| PRE-02 | Phase 2 | Pending |
| PRE-03 | Phase 2 | Pending |
| PRE-04 | Phase 2 | Pending |
| PRE-05 | Phase 2 | Pending |
| PRE-06 | Phase 2 | Pending |
| PRE-07 | Phase 2 | Pending |
| PRE-08 | Phase 2 | Pending |
| PRE-09 | Phase 2 | Pending |
| POST-01 | Phase 3 | Pending |
| POST-02 | Phase 3 | Pending |
| POST-03 | Phase 3 | Pending |
| POST-04 | Phase 3 | Pending |
| POST-05 | Phase 3 | Pending |
| POST-06 | Phase 3 | Pending |
| POST-07 | Phase 3 | Pending |
| POST-08 | Phase 3 | Pending |
| POST-09 | Phase 3 | Pending |
| POST-10 | Phase 3 | Pending |
| POST-11 | Phase 3 | Pending |
| POST-12 | Phase 3 | Pending |
| POST-13 | Phase 3 | Pending |
| TOURN-01 | Phase 4 | Pending |
| TOURN-02 | Phase 4 | Pending |
| TOURN-03 | Phase 4 | Pending |
| TOURN-04 | Phase 4 | Pending |
| TOURN-05 | Phase 4 | Pending |
| TOURN-06 | Phase 4 | Pending |
| TOURN-07 | Phase 4 | Pending |
| COMP-01 | Phase 2 | Pending |
| COMP-02 | Phase 2 | Pending |
| COMP-03 | Phase 2 | Pending |
| COMP-04 | Phase 2 | Pending |
| COMP-05 | Phase 2 | Pending |

**Coverage:**
- v1 requirements: 44 total
- Mapped to phases: 44
- Unmapped: 0

---
*Requirements defined: 2026-04-10*
*Last updated: 2026-04-10 after initial definition*
