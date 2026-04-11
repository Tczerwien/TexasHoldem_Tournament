<!-- GSD:project-start source:PROJECT.md -->
## Project

**MTTBot — IIT Poker Club Tournament Bot**

A competitive Texas Hold'em poker bot for the IIT Poker Club Multi-Table Tournament (MTT). The bot competes against all submitted student bots across 10 simulations, with points awarded to top-3 finishers (50/30/20). The goal is to win the tournament by maximizing aggregate points through consistent top-3 finishes with emphasis on first-place wins.

**Core Value:** Win the tournament — maximize aggregate points across 10 simulations by combining a high top-3 rate (~65%+) with aggressive play when in the money to push for 1st place finishes.

### Constraints

- **Deadline**: April 23, 2026 — 13 days from project start
- **Runtime**: 500ms hard timeout per decision — forced fold on timeout
- **Libraries**: Only math, random, numpy, pandas, engine.player_interface
- **File format**: Single .py file in `players/` directory
- **Class structure**: Must inherit from `Bot`, use `from engine.player_interface import Bot`
- **State**: All instance attributes must be picklable (no lambdas, file handles, locks)
- **No time module**: Use fixed iteration counts for MC loops instead
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### Core Runtime
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python 3.x | Engine-provided | Runtime | No choice -- engine dictates |
| `math` | stdlib | `log2`, `ceil`, `floor`, constants | Lightweight math ops, always available |
| `random` | stdlib | MC sampling (`random.sample`, `random.random`) | Faster than numpy for small-sample-from-large-population draws (50x faster per research). Critical for MC inner loop. |
| `numpy` | Engine-provided | Precomputation of lookup tables at module level | Vectorized table construction is fast; but numpy overhead per-call hurts for small operations in the hot path |
### Not Using
| Technology | Reason |
|------------|--------|
| `pandas` | Allowed but provides zero value for this use case. DataFrames add overhead with no benefit for numeric lookups or card manipulation. |
| `numpy` in hot path | For the MC inner loop (300-500 iterations of dealing ~5 cards from ~45), `random.sample()` is ~50x faster than `np.random.choice(replace=False)` for small samples from small populations. numpy's overhead dominates at these scales. Use numpy only at module-level precomputation time. |
| `itertools` | BLOCKED. Must implement `combinations(7,5)` manually -- only 21 combos, hardcode the indices. |
| `collections` | BLOCKED. Use plain dicts and lists instead. |
| `time` | BLOCKED. Use fixed iteration caps for MC loops. |
## Algorithm Stack -- Detailed
### 1. Hand Evaluator: Cactus Kev / Treys-Style Prime Product Lookup
- The treys library uses this exact algorithm and achieves ~250k evals/sec in pure Python
- Only requires dict lookups and integer multiplication -- no external dependencies
- Lookup tables are deterministic and can be built at module-level import time (free of 500ms budget)
- The engine already encodes cards in treys integer format, so bit extraction is trivial
### 2. 7-Card Combination Generation: Hardcoded Index Tuples
# Module-level constant -- all 21 ways to choose 5 from 7
### 3. Monte Carlo Equity Estimation: `random.sample` Inner Loop
- Population: ~45 remaining cards (52 - 2 hole - 3/4/5 board)
- Sample size: 2 (opponent hole) + 0/1/2 (remaining board) = 2-4 cards
- At this scale, `random.sample(remaining_deck, k)` is ~50x faster than `np.random.choice(remaining, k, replace=False)` because numpy's overhead (array creation, type checking, shuffle algorithm) dominates
- `random.sample` uses an O(k) selection algorithm internally, drawing only `k` random numbers
| Street | Unknown cards | Iterations | Why |
|--------|--------------|------------|-----|
| Flop (3 board) | 2 turn + 1 river + 2 villain = 5 | 300 | Most unknowns, slowest per-iter |
| Turn (4 board) | 1 river + 2 villain = 3 | 400 | Fewer unknowns, faster per-iter |
| River (5 board) | 2 villain = 2 | 500 | Fewest unknowns, fastest. Could enumerate C(45,2)=990 for exact equity but MC is fast enough |
- Per iteration: `random.sample` (~2us) + 2 * `evaluate_7` (~100us each for 21 dict lookups) = ~202us
- 300 iterations on flop: ~60ms
- 400 iterations on turn: ~70ms (slightly fewer lookups per iter since board is longer but same 7-card eval)
- Total MC time: 60-80ms, well within 250ms allocation, leaving 200ms+ buffer
### 4. Preflop: Chen Formula with Precomputed Lookup Table
- Well-established, deterministic, no randomness needed
- Maps all 169 hand categories (13x13 grid of rank pairs, suited/unsuited) to a numeric score
- Precomputable into a 169-entry dict at module level
- Directly usable for range thresholds (e.g., "open with Chen >= 5.0")
### 5. Push-Fold Tables: Precomputed Dict Lookup
- `SHOVE_TABLE`: 169 entries, value = max BB depth to open-shove
- `CALL_TABLE`: 169 entries, value = max villain BB depth to call their shove
### 6. Deck Construction: Treys-Compatible Integer Encoding
### 7. Lookup Table Construction: Build at Module Level
| Table | Entries | Build Time | Build Method |
|-------|---------|------------|--------------|
| `FULL_DECK` | 52 ints | <1ms | Loop over 13 ranks x 4 suits |
| `CHEN_TABLE` | 169 entries | <1ms | Chen formula over 169 hand categories |
| `SHOVE_TABLE` | 169 entries | <1ms | Hardcoded thresholds from strategy reference |
| `CALL_TABLE` | 169 entries | <1ms | Hardcoded thresholds from strategy reference |
| `FLUSH_LOOKUP` | ~1287 entries | ~5ms | Enumerate all flush hand prime products |
| `UNSUITED_LOOKUP` | ~4888 entries | ~5ms | Enumerate all non-flush hand prime products |
| `COMBO_INDICES` | 21 tuples | 0ms | Hardcoded constant |
## Performance Budget Analysis
### 500ms Decision Budget Breakdown
| Phase | Time | Method |
|-------|------|--------|
| Parse game_state | <1ms | Dict access |
| Stack/stage detection | <1ms | Arithmetic comparisons |
| Preflop (table lookup) | <1ms | Dict lookup for Chen/shove/call tables |
| Postflop MC equity | 60-80ms | 300-500 iterations of sample + evaluate |
| Draw detection | <2ms | Suit/rank counting on 5-7 cards |
| Board texture classification | <1ms | Rank/suit analysis |
| Decision logic | <2ms | Threshold comparisons |
| Pot accumulator update | <1ms | Simple arithmetic |
| Safety guards | <1ms | Bounds checking |
| **Total worst case** | **~90ms** | |
| **Safety buffer** | **~410ms** | 82% of budget unused |
## Critical Implementation Details
### Prime Extraction from Treys Cards
### Flush Detection Optimization
### Set Operations for MC Deck Filtering
## Alternatives Considered
| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Hand evaluator | Prime product lookup (treys-style) | Manual conditional classification (flush/straight/pair checks) | 5-10x slower due to Python branching overhead. Lookup tables are O(1) with no conditionals. |
| MC sampling | `random.sample()` | `numpy.random.Generator.choice(replace=False)` | numpy has array creation overhead that dominates at small sample sizes (2-5 cards from 45). random.sample is ~50x faster here. |
| MC iterations | Fixed caps (300/400/500) | Time-based adaptive (`time` module) | `time` module is BLOCKED. Fixed caps are predictable and benchmarkable. |
| Preflop evaluation | Chen formula lookup | Monte Carlo preflop equity | MC on preflop is wasteful -- 2 cards vs unknown is too noisy at 300 iters. Chen gives deterministic, precomputed scores that correlate well with actual equity. |
| River equity | MC 500 iterations | Exact enumeration C(45,2) = 990 | Exact enumeration is feasible on river (990 opponent combos x 21 eval each = 20,790 evals = ~80ms). Worth considering as an upgrade, but MC at 500 iters is sufficient and simpler. |
| Push-fold ranges | Precomputed tables | Real-time ICM calculation | ICM requires opponent stack info (unavailable) and is computationally expensive. Table-based ranges are proven and instant. |
| numpy in hot path | Avoid | Use for batch evaluation | numpy's per-call overhead (~10us for array creation) nullifies vectorization gains when individual operations are simple dict lookups. Only worth it for batch sizes >1000. |
## What NOT to Do
| Anti-Pattern | Why Dangerous |
|--------------|---------------|
| Use numpy in the MC inner loop | Array creation overhead dominates. `random.sample` + dict lookup is faster for this scale. |
| Implement hand evaluation with if/elif chains | O(n) branching is 5-10x slower than O(1) dict lookup. The lookup tables are small and fast. |
| Use pandas for anything | Zero value-add. DataFrames are for tabular data analysis, not real-time card evaluation. |
| Try to enumerate all opponent hand combos on flop | C(45,2) * C(43,2) * C(41,1) = too many combos. MC sampling is the only viable approach preflop/flop. |
| Build lookup tables inside `__init__` | Tables are the same for every instance. Module-level = built once and shared. `__init__` runs once per simulation (10 times total) -- wasteful. |
| Store numpy arrays in instance state | Pickling numpy arrays may fail depending on engine's pickle protocol. Stick to plain Python types for all `self.*` attributes. |
| Use `np.random.choice` with `replace=False` | For sampling 2-5 items from a 45-item list, Python's `random.sample` is ~50x faster due to numpy's overhead. |
## Installation / Setup
# No installation needed. All allowed modules are built-in or engine-provided.
# The complete bot is a single file: players/mtt_bot.py
# import numpy as np  -- available but not needed in the hot path
## Sources
- Treys evaluator algorithm: [ihendley/treys on GitHub](https://github.com/ihendley/treys) -- HIGH confidence
- Cactus Kev's poker hand evaluator: [suffe.cool/poker/evaluator.html](http://suffe.cool/poker/evaluator.html) -- HIGH confidence
- numpy.random.choice performance: [numpy/numpy#2764](https://github.com/numpy/numpy/issues/2764) -- HIGH confidence (random.sample ~50x faster for small samples)
- numpy.random.Generator.choice docs: [NumPy v2.4 Manual](https://numpy.org/doc/stable/reference/random/generated/numpy.random.Generator.choice.html) -- HIGH confidence
- Chen formula: [thepokerbank.com](https://www.thepokerbank.com/strategy/basic/starting-hand-selection/chen-formula/) -- HIGH confidence
- PHEvaluator perfect hash approach: [HenryRLee/PokerHandEvaluator](https://github.com/HenryRLee/PokerHandEvaluator) -- MEDIUM confidence (reference only, not using this approach)
- Hand rank boundaries (7462 distinct hands): [treys lookup.py](https://github.com/ihendley/treys/blob/master/treys/lookup.py) -- HIGH confidence
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
