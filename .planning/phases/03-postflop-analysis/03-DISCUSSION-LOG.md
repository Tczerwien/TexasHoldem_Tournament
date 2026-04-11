# Phase 3: Postflop Analysis - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-04-11
**Phase:** 03-postflop-analysis
**Areas discussed:** None (user deferred all to Claude)

---

## Gray Areas Presented

| Option | Description | Selected |
|--------|-------------|----------|
| Hand evaluator approach | Prime product lookup vs manual rank/suit evaluation -- tension between CLAUDE.md and REQUIREMENTS.md | |
| EHS draw bonuses | How much equity bonus for flush draws, OESDs, gutshots, combo draws | |
| You decide all | Let Claude make all implementation choices | ✓ |

**User's choice:** You decide all
**Notes:** Phase 3 is well-specified in CLAUDE.md algorithm stack. Key tension (prime product vs manual evaluator) resolved by Claude: Phase 3 implements manual approach per REQUIREMENTS.md POST-01, prime product deferred to v2 PERF-01.

---

## Claude's Discretion

All implementation decisions deferred to Claude, guided by CLAUDE.md algorithm stack and REQUIREMENTS.md POST-01 through POST-05.

## Deferred Ideas

- Cactus Kev prime product lookup (PERF-01) -- v2
- River exact enumeration (PERF-02) -- v2
- Adaptive MC iteration count (PERF-03) -- v2
