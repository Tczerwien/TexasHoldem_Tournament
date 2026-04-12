# Phase 1: Skeleton and Safety - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Crash-proof bot that loads in the MTT engine, completes all 10 simulations without crashing or timing out, plays every hand legally, and tracks game state across streets and hands. This phase produces a working (if strategically simple) bot skeleton that all subsequent phases build upon.

</domain>

<decisions>
## Implementation Decisions

### Default play style
- **D-01:** Tight-passive base strategy until Phase 2 adds real intelligence -- call when call_amount < 15% of stack, fold otherwise
- **D-02:** Raise with premium hands only (AA/KK/QQ) even in Phase 1, to avoid leaving obvious value on the table against the weak test field
- **D-03:** Always check when call_amount is 0 (never fold for free per SAFE-03)

### Bot identity
- **D-04:** Class name `HawkEyeBot`, inherits from `Bot`
- **D-05:** Display name `"HawkEye"` passed to `super().__init__()`
- **D-06:** File name `players/mtt_bot.py` per engine requirements (SAFE-09)

### Pot tracking strategy
- **D-07:** Detect new hand by checking `len(board_cards) == 0` combined with tracking last-seen board length to detect transitions
- **D-08:** Additive pot tracking -- on each get_action call, read pot_size from game_state (current-street bets); on new street (board length increased), add previous street's final pot_size to running total
- **D-09:** Reset pot accumulator and all per-hand state when new hand detected

### File structure
- **D-10:** Single file organized with comment banner sections: `# === CONSTANTS ===`, `# === PRECOMPUTATION ===`, `# === HELPERS ===`, `# === BOT CLASS ===`. Module-level code first, class definition last.
- **D-11:** Instance attributes use underscore prefix convention: `self._pot_total`, `self._hand_num`, `self._preflop_aggressor`, etc.
- **D-12:** Helper functions (guard, pot tracking, hand detection) are methods on the class, not module-level functions. Keeps state access simple via `self.*`.

### Claude's Discretion
- Exact premium hand detection logic (how to identify AA/KK/QQ from treys integer cards)
- Guard function internals (validation order, edge case handling)
- Exact section ordering within comment banners
- Error message formatting in try/except fallback

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Engine interface
- `Docs/MTT-Pokerbot-Engine/engine/player_interface.py` -- Bot base class, get_action signature, game_state dict structure
- `Docs/MTT-Pokerbot-Engine/engine/table.py` -- Betting round logic, pot_size calculation (line 138), current_bet reset (line 211), action handling (lines 156-188)

### Engine quirks
- `Docs/MTT-Pokerbot-Engine/engine/table.py` lines 55-56 -- Heads-up button posts BB (non-standard)
- `Docs/MTT-Pokerbot-Engine/engine/table.py` lines 182-186 -- Unknown action type defaults to check/fold (confirms ('check', 0) danger)

### Example bots
- `Docs/MTT-Pokerbot-Engine/players/call_bot.py` -- Minimal Bot implementation pattern (CallBot)
- `Docs/MTT-Pokerbot-Engine/players/random_bot.py` -- Example with raise logic

### Requirements
- `.planning/REQUIREMENTS.md` -- SAFE-01 through SAFE-09, STATE-01 through STATE-04

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- No existing bot code to reuse -- this is the first phase, creating the file from scratch

### Established Patterns
- Engine uses treys integer card encoding: rank = `((card >> 8) & 0xF) + 2`, suit = `(card >> 12) & 0xF`
- Engine returns actions as tuples: `('fold', 0)`, `('call', 0)`, `('raise', amount)`
- Engine wraps bot calls in ThreadPoolExecutor with 500ms timeout, defaults to fold on timeout or exception

### Integration Points
- File must be at `players/mtt_bot.py` for engine auto-discovery
- Class must inherit from `Bot` via `from engine.player_interface import Bot`
- Single Bot subclass per file (engine scans for subclasses)

</code_context>

<specifics>
## Specific Ideas

- Bot named "HawkEye" after IIT Scarlet Hawks mascot -- should appear on tournament leaderboard with this name
- Created by Thomas (Polish CS student) and Furquan at Illinois Institute of Technology

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 01-skeleton-and-safety*
*Context gathered: 2026-04-10*
