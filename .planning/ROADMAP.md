# Roadmap: MTTBot

## Overview

Build a competitive Texas Hold'em tournament bot in 5 phases, each producing a working (if limited) bot. Phase 1 creates a crash-proof skeleton that plays legally. Phase 2 adds preflop intelligence with Chen formula hand evaluation and push-fold logic. Phase 3 builds the postflop analysis engine (hand evaluator, Monte Carlo equity, draw detection). Phase 4 wires postflop analysis into betting decisions (c-bets, pot odds, sizing). Phase 5 adds tournament stage awareness, ICM pressure, and field exploitation to produce the submission-ready bot.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Skeleton and Safety** - Crash-proof bot that loads, plays legally, and tracks game state
- [ ] **Phase 2: Preflop Engine** - Bot makes intelligent preflop decisions with hand evaluation and push-fold tables
- [ ] **Phase 3: Postflop Analysis** - Hand evaluator, Monte Carlo equity, draw detection, and board texture classification
- [ ] **Phase 4: Postflop Decisions** - C-bet logic, pot odds, bet sizing, and stack commitment rules
- [ ] **Phase 5: Tournament Awareness** - Stage detection, ICM pressure, bubble play, heads-up, and field exploitation

## Phase Details

### Phase 1: Skeleton and Safety
**Goal**: Bot loads in the engine, completes all 10 simulations without crashing, and plays every hand legally
**Depends on**: Nothing (first phase)
**Requirements**: SAFE-01, SAFE-02, SAFE-03, SAFE-04, SAFE-05, SAFE-06, SAFE-07, SAFE-08, SAFE-09, STATE-01, STATE-02, STATE-03, STATE-04
**Success Criteria** (what must be TRUE):
  1. Bot loads in the MTT engine and completes 10 full simulations with zero crashes or timeouts
  2. Bot never folds when call_amount is 0 (always checks instead) and never returns ('check', 0)
  3. All raise amounts are capped at stack_size and floored to min_raise -- no illegal bet sizes
  4. Pot accumulator correctly tracks total pot across streets (not just current-street bets)
  5. Hand boundary detection correctly resets per-hand state and increments hand counter
**Plans:** 2 plans
Plans:
- [x] 01-01-PLAN.md -- Bot skeleton with safety guards, try/except wrapper, tight-passive logic, and safety test harness
- [x] 01-02-PLAN.md -- State tracking (pot accumulator, hand detection, aggressor flag, hand counter) and state test suite

### Phase 2: Preflop Engine
**Goal**: Bot makes correct preflop decisions based on hand strength, stack depth, and situation
**Depends on**: Phase 1
**Requirements**: PRE-01, PRE-02, PRE-03, PRE-04, PRE-05, PRE-06, PRE-07, PRE-08, PRE-09, COMP-01, COMP-02, COMP-03, COMP-04, COMP-05
**Success Criteria** (what must be TRUE):
  1. Bot opens with approximately correct range widths by stack mode (deep ~20%, medium ~15%, shallow reshove-only)
  2. Bot shoves all-in with correct push-fold ranges when below 15BB and folds trash
  3. Bot correctly identifies situation (RFI, facing open, facing 3-bet, BB option, SB complete) and adjusts hand requirements
  4. All lookup tables (Chen scores, shove table, call table, full deck) are precomputed at module level and do not consume per-decision time budget
  5. AA/KK 4-bets facing a 3-bet; QQ+/AKs 3-bets facing an open
**Plans:** 2 plans
Plans:
- [ ] 02-01-PLAN.md -- Module-level lookup tables (FULL_DECK, CHEN_TABLE, SHOVE_TABLE, CALL_TABLE) and table validation tests
- [ ] 02-02-PLAN.md -- Preflop decision engine (_preflop, stack mode, situation detection, 3bet/4bet, raise sizing) and behavior tests

### Phase 3: Postflop Analysis
**Goal**: Bot can evaluate hand strength, estimate equity via Monte Carlo, detect draws, and classify board texture
**Depends on**: Phase 2
**Requirements**: POST-01, POST-02, POST-03, POST-04, POST-05
**Success Criteria** (what must be TRUE):
  1. 7-card hand evaluator correctly ranks all standard poker hands (high card through straight flush) by evaluating C(7,5) combinations
  2. Monte Carlo equity estimation produces plausible values (AA on random board ~0.85, 72o ~0.35) within iteration caps (300/400/500 by street)
  3. Draw detection correctly identifies flush draws, OESDs, gutshots, and combo draws from hole cards + board
  4. Board texture classification distinguishes dry, semi-wet, wet, and paired boards
  5. Effective Hand Strength combines MC equity with draw bonus into a single usable EHS value
**Plans**: TBD

### Phase 4: Postflop Decisions
**Goal**: Bot makes correct postflop betting decisions using the analysis engine from Phase 3
**Depends on**: Phase 3
**Requirements**: POST-06, POST-07, POST-08, POST-09, POST-10, POST-11, POST-12, POST-13
**Success Criteria** (what must be TRUE):
  1. Bot fires c-bets on the flop when it was the preflop aggressor and has sufficient hand strength, considering board texture
  2. Bot correctly folds when EHS is well below required equity (pot odds) and calls/raises when EHS exceeds the threshold
  3. Bet sizing varies by street, texture, and situation (33-75% pot) rather than using fixed sizes
  4. Bot shoves instead of betting when the bet would commit 60%+ of its stack (stack commitment rule)
  5. Bot barrels the turn with strong+ hands and value bets the river with strong+ hands
**Plans**: TBD

### Phase 5: Tournament Awareness
**Goal**: Bot adjusts strategy for tournament stages, applies ICM pressure at bubble, and exploits weak fields to maximize tournament points
**Depends on**: Phase 4
**Requirements**: TOURN-01, TOURN-02, TOURN-03, TOURN-04, TOURN-05, TOURN-06, TOURN-07
**Success Criteria** (what must be TRUE):
  1. Bot correctly detects tournament stage (early/middle/late/bubble/ITM/heads-up) from blind level and active player count
  2. Bot applies 1.4x ICM calling multiplier at bubble -- folding significantly more all-in calls than in early game
  3. At bubble, big stack opens wider to bully while medium stack tightens to survive into the money
  4. When in the money (3 players left), bot releases ICM pressure and plays aggressively to fight for 1st place
  5. In heads-up play, bot opens 55%+ of hands and correctly handles the button-posts-BB engine quirk

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Skeleton and Safety | 2/2 | Complete | 2026-04-11 |
| 2. Preflop Engine | 0/2 | Planned | - |
| 3. Postflop Analysis | 0/TBD | Not started | - |
| 4. Postflop Decisions | 0/TBD | Not started | - |
| 5. Tournament Awareness | 0/TBD | Not started | - |
