# HawkEyeBot: a Texas Hold'em tournament bot

A poker bot for the IIT Poker Club's bot tournament (April 2026), where student bots played multi-table Texas Hold'em tournaments against each other. It finished 2nd of 3 entries.

**How it was made:** Claude Code, an AI coding agent, wrote the code, the tests and the documents in `Docs/` under my direction.

## What's inside

- `players/mtt_bot.py`: the whole bot in one file (about 1,450 lines), as the tournament required.
  - **Before the flop:** hand strength from the Chen formula, and push-or-fold charts when the stack is short.
  - **After the flop:** a seven-card hand evaluator, Monte Carlo simulation to estimate the chance of winning, draw detection and pot odds.
  - **Tournament play:** adjusts to the stage (early, near the money, in the money, heads-up) and to its stack size.
- `tests/`: 217 tests. They stand in a mock for the tournament's engine, so they run without it.
- `Docs/`: the tournament rules and engine interface, plus the strategy and build specification.

The tournament engine itself belongs to the club and isn't included, so the bot runs only inside the club's tournament program. To run the tests:

```sh
python -m pytest tests
```
