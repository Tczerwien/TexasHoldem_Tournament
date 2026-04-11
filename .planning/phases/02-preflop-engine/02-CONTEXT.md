# Phase 2: Preflop Engine - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Intelligent preflop decisions using Chen formula hand evaluation, stack-depth-based opening ranges, push-fold shove/call tables, position inference, and situational strategy (RFI, facing open, facing 3-bet, BB option, SB complete). This phase replaces Phase 1's tight-passive default with real preflop intelligence. All lookup tables are precomputed at module level (free of 500ms budget).

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

User explicitly deferred all implementation decisions to Claude. The following areas are guided by CLAUDE.md algorithm stack and REQUIREMENTS.md specifications but Claude has flexibility on exact implementation details:

- **D-01:** Chen formula implementation -- 169-entry lookup table mapping (rank1, rank2, suited) tuples to numeric scores. Precomputed at module level. Standard Chen formula from thepokerbank.com reference.
- **D-02:** Stack mode detection -- thresholds from PRE-02: deep >= 40BB, medium >= 25BB, shallow >= 15BB, push-fold < 15BB. BB computed from `game_state["blinds"]["big"]`.
- **D-03:** Opening range widths by stack mode -- deep ~20% (Chen >= ~5), medium ~15% (Chen >= ~7), shallow reshove-only. Exact Chen thresholds are Claude's call.
- **D-04:** Push-fold shove table -- 169-entry dict mapping hand categories to max BB depth for open-shoving. Source: standard tournament push-fold charts. Claude picks specific ranges.
- **D-05:** Push-fold call table -- 169-entry dict mapping hand categories to max villain BB depth for calling their shove. Claude picks specific ranges.
- **D-06:** Position inference from call_amount relative to blinds -- RFI (call_amount == big_blind), facing open (call_amount > big_blind but < ~6x), facing 3-bet (call_amount >= ~6x big_blind), BB option (call_amount == 0 in BB), SB complete (call_amount == small_blind). Claude determines exact thresholds.
- **D-07:** Situational preflop strategy -- different hand requirements per situation (PRE-07). Claude designs the decision flow and thresholds.
- **D-08:** 3-bet logic: QQ+/AKs facing an open. 4-bet logic: AA/KK facing a 3-bet (PRE-08). Exact range representation is Claude's call.
- **D-09:** Preflop raise sizing: 2.5x BB deep, 2.2x BB medium, 2.0x BB shallow, shove push-fold (PRE-09). Claude handles edge cases.
- **D-10:** Full 52-card deck at module level in treys integer encoding (COMP-01). Claude picks construction approach.
- **D-11:** How to integrate with existing _decide() -- Phase 2 replaces the tight-passive logic but preserves the _detect_new_hand/_update_pot calls and _guard() pipeline.
- **D-12:** Decision tree organization -- how RFI/facing open/facing 3-bet/BB option/SB complete branches are structured in code for later Phase 5 modification.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Engine interface
- `Docs/MTT-Pokerbot-Engine/engine/player_interface.py` -- Bot base class, game_state dict structure
- `Docs/MTT-Pokerbot-Engine/engine/table.py` -- How raises work (line 165: amount is additive on top of call), min_raise handling

### Existing bot code
- `players/mtt_bot.py` -- Current HawkEyeBot skeleton from Phase 1. Phase 2 modifies this file.

### Requirements
- `.planning/REQUIREMENTS.md` -- PRE-01 through PRE-09, COMP-01 through COMP-05

### Algorithm references
- `CLAUDE.md` "Algorithm Stack" section -- Chen formula, push-fold tables, deck construction, performance budget

### Prior phase context
- `.planning/phases/01-skeleton-and-safety/01-CONTEXT.md` -- File structure decisions (D-10 through D-12) that Phase 2 must follow

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_is_premium()` -- Already extracts ranks via `((card >> 8) & 0xF) + 2`. Phase 2 replaces this with Chen formula but the bit extraction pattern is reusable.
- `_guard()` -- All actions pass through guard. Phase 2 doesn't modify guard.
- `_detect_new_hand()` / `_update_pot()` -- State tracking stays as-is. Phase 2 calls these at top of `_decide()`.

### Established Patterns
- Comment banner sections: `# === CONSTANTS ===`, `# === PRECOMPUTATION ===`, etc.
- Underscore prefix for instance attributes
- All helpers as class methods

### Integration Points
- `_decide()` -- Replace tight-passive body with preflop engine. Keep existing hand detection and pot tracking calls.
- `# === CONSTANTS ===` section -- Add FULL_DECK, CHEN_TABLE, SHOVE_TABLE, CALL_TABLE
- `# === PRECOMPUTATION ===` section -- Add module-level table construction code

</code_context>

<specifics>
## Specific Ideas

No specific requirements -- user deferred all implementation choices to Claude with guidance from CLAUDE.md algorithm stack and REQUIREMENTS.md specifications.

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 02-preflop-engine*
*Context gathered: 2026-04-11*
