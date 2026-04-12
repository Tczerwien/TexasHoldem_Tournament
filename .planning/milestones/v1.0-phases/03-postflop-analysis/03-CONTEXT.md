# Phase 3: Postflop Analysis - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Postflop analysis engine: 7-card hand evaluator, Monte Carlo equity estimation with fixed iteration caps, draw detection (flush draw, OESD, gutshot, combo draw), board texture classification (dry/semi-wet/wet/paired), and Effective Hand Strength (EHS) combining MC equity with draw bonus. This phase builds the analysis tools -- Phase 4 wires them into betting decisions.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

User explicitly deferred all implementation decisions to Claude. The following areas are guided by CLAUDE.md algorithm stack and REQUIREMENTS.md specifications:

- **D-01:** Hand evaluator approach -- CLAUDE.md specifies Cactus Kev/treys-style prime product lookup tables for O(1) evaluation. However, REQUIREMENTS.md POST-01 says "no treys library -- manual rank/suit evaluation of C(7,5) combos". Claude resolves this tension: implement a manual rank/suit evaluator that classifies hands by checking flush, straight, pairs/trips/quads from the 5-card combos. The prime product approach from CLAUDE.md is a v2 optimization (PERF-01). Phase 3 uses the simpler manual approach that satisfies POST-01.
- **D-02:** Hand ranking -- return a numeric rank where lower is better (consistent with treys convention). Must correctly rank: high card, pair, two pair, three of a kind, straight, flush, full house, four of a kind, straight flush. Use rank boundaries from treys (7462 distinct hand values).
- **D-03:** 7-card evaluation -- evaluate all C(7,5)=21 combinations using COMBO_INDICES (already in code). Return the best (lowest) rank among all 21 five-card hands.
- **D-04:** Monte Carlo equity estimation -- `random.sample()` inner loop per CLAUDE.md. Fixed iteration caps: 300 flop, 400 turn, 500 river (POST-02). Sample remaining cards from deck minus known cards, evaluate both hands, count wins/ties/losses.
- **D-05:** Draw detection -- check hole cards + board for flush draws (4 cards of same suit), OESDs (4 consecutive ranks possible), gutshots (1 card fills inside straight), combo draws (flush draw + straight draw). Returns draw type flags (POST-03).
- **D-06:** Board texture classification -- DRY (no flush draw possible, no connected cards), SEMI_WET (some draws possible), WET (flush draw + straight draw possible), PAIRED (board has a pair). Based on suit/rank analysis of board cards (POST-05).
- **D-07:** Effective Hand Strength (EHS) -- combine raw MC equity with draw bonus. EHS = mc_equity + draw_bonus. Draw bonus values: flush draw ~0.06, OESD ~0.05, gutshot ~0.03, combo draw ~0.09. Claude determines exact values (POST-04).
- **D-08:** Performance budget -- hand evaluator must stay within ~60-80ms total for MC loop (300-500 iterations x 2 evaluations each). Manual evaluator should target ~200us per 7-card eval (21 five-card checks with conditional classification).
- **D-09:** Deck filtering for MC -- use set operations to exclude known cards (hole + board) from FULL_DECK before sampling. `remaining = [c for c in FULL_DECK if c not in known_set]` where known_set is a Python set for O(1) lookup.
- **D-10:** All new analysis functions as class methods on HawkEyeBot per Phase 1 D-12. Module-level helpers/constants go in the appropriate banner sections.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Engine interface
- `Docs/MTT-Pokerbot-Engine/engine/player_interface.py` -- game_state dict with hole_cards and board_cards
- `Docs/MTT-Pokerbot-Engine/engine/table.py` -- Card dealing, board construction

### Existing bot code
- `players/mtt_bot.py` -- Current HawkEyeBot with FULL_DECK, COMBO_INDICES, treys bit extraction

### Requirements
- `.planning/REQUIREMENTS.md` -- POST-01 through POST-05

### Algorithm references
- `CLAUDE.md` "Algorithm Stack" sections 1-3 -- Hand evaluator, combination generation, Monte Carlo equity
- `CLAUDE.md` "Performance Budget Analysis" -- Timing targets for MC loop

### Prior phase context
- `.planning/phases/01-skeleton-and-safety/01-CONTEXT.md` -- File structure decisions (D-10 through D-12)
- `.planning/phases/02-preflop-engine/02-CONTEXT.md` -- Full discretion precedent, table construction patterns

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `FULL_DECK` (52 treys-encoded cards) -- used as population for MC sampling
- `COMBO_INDICES` (21 tuples for C(7,5)) -- used by 7-card evaluator
- Treys bit extraction: `rank_int = (card >> 8) & 0xF`, `suit_int = (card >> 12) & 0xF`
- `_PRIMES` list -- available for prime product approach if needed

### Established Patterns
- Module-level constants and precomputation in banner sections
- Class methods with underscore prefix
- `_guard()` wraps all action returns
- `_decide()` as entry point, routing to `_preflop()` for preflop

### Integration Points
- `_decide()` -- Phase 4 will add postflop routing here using Phase 3's analysis functions
- `est_pot` from `_update_pot()` -- available for pot odds calculations in Phase 4
- `_was_preflop_aggressor` -- Phase 4 uses for c-bet decisions

</code_context>

<specifics>
## Specific Ideas

No specific requirements -- user deferred all implementation choices to Claude with guidance from CLAUDE.md algorithm stack and REQUIREMENTS.md specifications.

Key tension resolved: CLAUDE.md describes prime product lookup (treys-style) as the recommended evaluator, but REQUIREMENTS.md POST-01 mandates "manual rank/suit evaluation." Phase 3 implements the manual approach. The prime product optimization is deferred to v2 (PERF-01).

</specifics>

<deferred>
## Deferred Ideas

- Cactus Kev prime product lookup evaluator (PERF-01) -- v2 optimization
- River exact enumeration instead of MC (PERF-02) -- v2 optimization
- Adaptive MC iteration count (PERF-03) -- v2 optimization

</deferred>

---

*Phase: 03-postflop-analysis*
*Context gathered: 2026-04-11*
