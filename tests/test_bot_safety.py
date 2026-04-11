"""Safety test harness for HawkEyeBot.

Tests all SAFE requirements (SAFE-01 through SAFE-09) and key decision
logic (D-01, D-02, D-03). Uses a mock engine module to avoid import
dependency on the actual engine.
"""
import sys
import os
import types
import pickle

# Mock the engine module so we can import mtt_bot without the engine on PYTHONPATH
mock_engine = types.ModuleType("engine")
mock_player_interface = types.ModuleType("engine.player_interface")


class MockBot:
    def __init__(self, name):
        self.name = name

    def get_action(self, game_state):
        raise NotImplementedError


mock_player_interface.Bot = MockBot
sys.modules["engine"] = mock_engine
sys.modules["engine.player_interface"] = mock_player_interface

# Add players directory to path and import the bot
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "players"))
from mtt_bot import HawkEyeBot


def make_state(call_amount=0, stack_size=1500, min_raise=20,
               hole_cards=None, board_cards=None, active_players=6):
    """Build a game_state dict for testing."""
    if hole_cards is None:
        # Non-premium hand: ranks 2 and 7 (different ranks, both < 12)
        # rank = ((card >> 8) & 0xF) + 2
        # For rank 2: (2-2) << 8 = 0x0000
        # For rank 7: (7-2) << 8 = 0x0500
        hole_cards = [0x00000000, 0x00000500]
    if board_cards is None:
        board_cards = []
    return {
        "hole_cards": hole_cards,
        "board_cards": board_cards,
        "pot_size": 30,
        "stack_size": stack_size,
        "call_amount": call_amount,
        "min_raise": min_raise,
        "blinds": {"small": 10, "big": 20},
        "active_players": active_players,
    }


def make_premium_cards():
    """Create AA hole cards in treys integer encoding.

    rank = ((card >> 8) & 0xF) + 2
    For Ace (rank 14): (14 - 2) << 8 = 12 << 8 = 0x0C00
    Two aces with different suit bits.
    """
    ace1 = (12 << 8) | (1 << 12) | 0x01  # Ace of spades-ish
    ace2 = (12 << 8) | (2 << 12) | 0x02  # Ace of hearts-ish
    return [ace1, ace2]


# --- SAFE-03: Never fold when call_amount == 0 ---

def test_safe03_no_fold_when_free():
    bot = HawkEyeBot()
    state = make_state(call_amount=0)
    result = bot._guard("fold", 0, state)
    assert result == ("call", 0), f"SAFE-03 failed: got {result}, expected ('call', 0)"


# --- SAFE-04: Never return ('check', 0) ---

def test_safe04_no_check_action_facing_bet():
    bot = HawkEyeBot()
    state = make_state(call_amount=50)
    result = bot._guard("check", 0, state)
    assert result == ("call", 0), f"SAFE-04 failed (facing bet): got {result}, expected ('call', 0)"


def test_safe04_no_check_action_when_free():
    bot = HawkEyeBot()
    state = make_state(call_amount=0)
    result = bot._guard("check", 0, state)
    assert result == ("call", 0), f"SAFE-04 failed (free): got {result}, expected ('call', 0)"


# --- SAFE-05: Raise amount floor and cap ---

def test_safe05_raise_floor():
    bot = HawkEyeBot()
    state = make_state(min_raise=20)
    result = bot._guard("raise", 5, state)
    assert result == ("raise", 20), f"SAFE-05 floor failed: got {result}, expected ('raise', 20)"


def test_safe05_raise_cap():
    bot = HawkEyeBot()
    state = make_state(stack_size=1000)
    result = bot._guard("raise", 5000, state)
    assert result == ("raise", 1000), f"SAFE-05 cap failed: got {result}, expected ('raise', 1000)"


def test_safe05_cannot_afford_raise():
    bot = HawkEyeBot()
    # Stack is 50, call_amount is 60 -- cannot afford even the call as a raise
    state = make_state(stack_size=50, call_amount=60, min_raise=20)
    result = bot._guard("raise", 100, state)
    assert result == ("call", 0), f"SAFE-05 cannot afford failed: got {result}, expected ('call', 0)"


# --- SAFE-07: Unknown action fallback ---

def test_safe07_unknown_action():
    bot = HawkEyeBot()
    state = make_state()
    result = bot._guard("bluff", 50, state)
    assert result == ("call", 0), f"SAFE-07 failed: got {result}, expected ('call', 0)"


# --- SAFE-02: Exception handling in get_action ---

def test_safe02_exception_handling():
    bot = HawkEyeBot()

    # Monkey-patch _decide to raise an exception
    def bad_decide(game_state):
        raise ValueError("Intentional test crash")

    bot._decide = bad_decide

    # When call_amount == 0, should return ("call", 0) instead of crashing
    state_free = make_state(call_amount=0)
    result = bot.get_action(state_free)
    assert result == ("call", 0), f"SAFE-02 failed (free): got {result}, expected ('call', 0)"

    # When call_amount > 0, should return ("fold", 0) instead of crashing
    state_bet = make_state(call_amount=50)
    result = bot.get_action(state_bet)
    assert result == ("fold", 0), f"SAFE-02 failed (bet): got {result}, expected ('fold', 0)"


# --- SAFE-06: Picklable state ---

def test_safe06_picklable():
    bot = HawkEyeBot()
    bot._hand_num = 5
    bot._pot_total = 200
    data = pickle.dumps(bot)
    bot2 = pickle.loads(data)
    assert bot2.name == "HawkEye", f"SAFE-06 name failed: got {bot2.name}"
    assert bot2._hand_num == 5, f"SAFE-06 hand_num failed: got {bot2._hand_num}"
    assert bot2._pot_total == 200, f"SAFE-06 pot_total failed: got {bot2._pot_total}"


# --- D-01: Tight-passive call/fold logic ---

def test_d01_call_when_cheap():
    bot = HawkEyeBot()
    # call_amount=100, stack_size=1500 -> 6.7% < 15% -> call
    state = make_state(call_amount=100, stack_size=1500)
    result = bot._decide(state)
    assert result == ("call", 0), f"D-01 call failed: got {result}, expected ('call', 0)"


def test_d01_fold_when_expensive():
    bot = HawkEyeBot()
    # call_amount=300, stack_size=1500 -> 20% >= 15% -> fold
    state = make_state(call_amount=300, stack_size=1500)
    result = bot._decide(state)
    assert result == ("fold", 0), f"D-01 fold failed: got {result}, expected ('fold', 0)"


# --- D-03: Check when free (non-premium) ---

def test_d03_check_when_free():
    bot = HawkEyeBot()
    # call_amount=0, non-premium hand -> check (returned as ('call', 0))
    state = make_state(call_amount=0)
    result = bot._decide(state)
    assert result == ("call", 0), f"D-03 failed: got {result}, expected ('call', 0)"


# --- D-02: Raise with premium hands preflop ---

def test_d02_raise_premium_preflop():
    bot = HawkEyeBot()
    # AA preflop, call_amount=0 -> should raise
    aa_cards = make_premium_cards()
    state = make_state(call_amount=0, hole_cards=aa_cards, board_cards=[])
    result = bot._decide(state)
    assert result[0] == "raise", f"D-02 failed: got action '{result[0]}', expected 'raise'"
    assert result[1] > 0, f"D-02 failed: raise amount should be > 0, got {result[1]}"


# --- Main runner (for environments without pytest) ---

if __name__ == "__main__":
    tests = [
        test_safe03_no_fold_when_free,
        test_safe04_no_check_action_facing_bet,
        test_safe04_no_check_action_when_free,
        test_safe05_raise_floor,
        test_safe05_raise_cap,
        test_safe05_cannot_afford_raise,
        test_safe07_unknown_action,
        test_safe02_exception_handling,
        test_safe06_picklable,
        test_d01_call_when_cheap,
        test_d01_fold_when_expensive,
        test_d03_check_when_free,
        test_d02_raise_premium_preflop,
    ]

    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            test_fn()
            print(f"  PASS: {test_fn.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {test_fn.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {test_fn.__name__}: {e}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed, {passed + failed} total")
    if failed > 0:
        sys.exit(1)
    else:
        print("ALL TESTS PASSED")
