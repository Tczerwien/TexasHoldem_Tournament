# MTTBot — IIT Poker Club Tournament Bot

## What This Is

A competitive Texas Hold'em poker bot for the IIT Poker Club Multi-Table Tournament (MTT). The bot competes against all submitted student bots across 10 simulations, with points awarded to top-3 finishers (50/30/20). The goal is to win the tournament by maximizing aggregate points through consistent top-3 finishes with emphasis on first-place wins.

## Core Value

Win the tournament — maximize aggregate points across 10 simulations by combining a high top-3 rate (~65%+) with aggressive play when in the money to push for 1st place finishes.

## Requirements

### Validated

- [x] Bot class inheriting from `Bot` with correct import form — Validated in Phase 1
- [x] Safety guards: try/except wrapper, never fold for free, never use `('check', 0)`, cap raises at stack — Validated in Phase 1
- [x] Pot accumulator workaround for broken `pot_size` — Validated in Phase 1
- [x] All instance state picklable (basic Python types only) — Validated in Phase 1
- [x] Complete bot in single file `players/mtt_bot.py` — Validated in Phase 1

### Active

- [ ] Bot class inheriting from `Bot` with correct import form (`from engine.player_interface import Bot`)
- [ ] Safety guards: try/except wrapper, never fold for free, never use `('check', 0)`, cap raises at stack
- [ ] Pot accumulator workaround for broken `pot_size` (current-street only bug)
- [ ] Stack mode detection (deep/medium/shallow/push-fold by BB thresholds)
- [ ] Tournament stage detection (early/middle/late/bubble/ITM/heads-up from blind level + active_players)
- [ ] Preflop hand classification via Chen formula with precomputed lookup table
- [ ] Preflop opening ranges by stack mode (deep ~20%, medium ~15%, shallow reshove-only)
- [ ] Preflop situational strategy (RFI, facing open, facing 3-bet, BB option, SB complete)
- [ ] Push-fold shove table (<15BB) with stack-depth-dependent ranges
- [ ] Push-fold call table (facing shove) with villain-stack-dependent ranges
- [ ] Monte Carlo postflop equity estimation (300/400/500 iterations by street)
- [ ] 7-card hand evaluator (no treys library — manual rank/suit evaluation of C(7,5) combos)
- [ ] C-bet logic with preflop aggressor tracking and board texture awareness
- [ ] Pot odds call/fold decisions with required equity calculation
- [ ] ICM multiplier at bubble (1.4x call threshold for all-in decisions)
- [ ] Draw detection (flush draw, OESD, gutshot, combo) with EHS bonus
- [ ] Board texture classification (dry/semi-wet/wet/paired)
- [ ] Bet sizing system (preflop by stack mode, postflop by street/texture/situation)
- [ ] Stack commitment rule (bet >= 60% stack -> shove instead)
- [ ] Module-level precomputation of all lookup tables (free of 500ms budget)
- [ ] All instance state picklable (basic Python types only)
- [ ] Complete bot in single file `players/mtt_bot.py`

### Out of Scope

- Opponent modeling — no action_history available in game_state
- Multi-street bluff sequences — complexity not justified for v1
- Dynamic raise sizing based on opponent tendencies — no data available
- Machine learning / neural network approaches — blocked libraries
- Multi-file architecture — single file submission required

## Context

- **Tournament engine:** MTT-Pokerbot-Engine by Alex Addison, source available at `Docs/MTT-Pokerbot-Engine/`
- **Test field:** 50 TestBots (random call/fold), 1 CallBot (always call), 1 RandomBot (20/60/20 fold/call/raise). Real tournament will include unknown student submissions.
- **Engine quirks verified from source:**
  - `pot_size` only shows current-street bets (pot_manager.collect_bets() called only at showdown)
  - Button posts BB in heads-up (non-standard)
  - Turn/river draw wastes one card per street (benign)
  - `('check', 0)` is not recognized — folds you if call_amount > 0
  - `position` field advertised in docstring but NOT in actual game_state
- **Card encoding:** Treys integer format, decoded via bit operations (rank: `((card >> 8) & 0xF) + 2`, suit: `(card >> 12) & 0xF`)
- **Allowed imports:** `math`, `random`, `numpy`, `pandas`, `engine.player_interface` — AST-scanned, violations block the bot for all 10 sims
- **The PDF template showing a bare `get_action()` function is misleading** — engine loader requires a class inheriting from Bot

## Constraints

- **Deadline**: April 23, 2026 — 13 days from project start
- **Runtime**: 500ms hard timeout per decision — forced fold on timeout
- **Libraries**: Only math, random, numpy, pandas, engine.player_interface
- **File format**: Single .py file in `players/` directory
- **Class structure**: Must inherit from `Bot`, use `from engine.player_interface import Bot`
- **State**: All instance attributes must be picklable (no lambdas, file handles, locks)
- **No time module**: Use fixed iteration counts for MC loops instead

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Single Bot class + module-level helpers | Engine scans for Bot subclasses; multiple would register as separate players | -- Pending |
| Chen formula for preflop hand ranking | Fast, well-established, precomputable into 169-entry lookup table | -- Pending |
| Monte Carlo for postflop equity | Only viable approach within allowed libraries; iteration-capped for timing | -- Pending |
| Manual 7-card evaluator | Treys library blocked; must implement rank/suit evaluation from scratch | -- Pending |
| Balanced-aggressive tournament strategy | Math shows 65% top-3 rate at avg 1.6th finish = ~303 pts over 10 sims (best EV) | -- Pending |
| Pot accumulator workaround | pot_size bug is confirmed from source; must track cross-street pot manually | -- Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-11 after Phase 1 completion*
