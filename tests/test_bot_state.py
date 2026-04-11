"""State tracking test suite for HawkEyeBot.

Tests all STATE requirements (STATE-01 through STATE-04) plus edge cases
for hand boundary detection and pot accumulation. Uses a mock engine module
to avoid import dependency on the actual engine.
"""
import sys
import os
import types

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


def make_state(board_cards=None, pot_size=30, call_amount=0,
               stack_size=1500, min_raise=20, hole_cards=None):
    """Build a game_state dict for testing."""
    if board_cards is None:
        board_cards = []
    if hole_cards is None:
        # Non-premium hand: ranks 2 and 7 (different ranks, both < 12)
        # rank = ((card >> 8) & 0xF) + 2
        # For rank 2: (2-2) << 8 = 0x0000
        # For rank 7: (7-2) << 8 = 0x0500
        hole_cards = [0x00000000, 0x00000500]
    return {
        "hole_cards": hole_cards,
        "board_cards": board_cards,
        "pot_size": pot_size,
        "stack_size": stack_size,
        "call_amount": call_amount,
        "min_raise": min_raise,
        "blinds": {"small": 10, "big": 20},
        "active_players": 6,
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


# --- STATE-01: Pot accumulator across streets ---

def test_state01_pot_accumulator_across_streets():
    """Verify pot accumulates correctly across a full hand.

    Preflop pot_size=30, flop pot_size=60, turn pot_size=40, river pot_size=80.
    Total should accumulate: 30, then 30+60=90, then 90+40=130, then 130+80=210.
    """
    bot = HawkEyeBot()

    # Preflop: board_cards=[], pot_size=30
    gs_preflop = make_state(board_cards=[], pot_size=30)
    bot.get_action(gs_preflop)
    assert bot._street_pot == 30, f"Preflop street_pot: expected 30, got {bot._street_pot}"
    assert bot._pot_total == 0, f"Preflop pot_total: expected 0, got {bot._pot_total}"

    # Flop: board_cards=[1,2,3], pot_size=60
    gs_flop = make_state(board_cards=[1, 2, 3], pot_size=60)
    bot.get_action(gs_flop)
    assert bot._pot_total == 30, f"Flop pot_total: expected 30, got {bot._pot_total}"
    assert bot._street_pot == 60, f"Flop street_pot: expected 60, got {bot._street_pot}"
    total_flop = bot._pot_total + bot._street_pot
    assert total_flop == 90, f"Flop total: expected 90, got {total_flop}"

    # Turn: board_cards=[1,2,3,4], pot_size=40
    gs_turn = make_state(board_cards=[1, 2, 3, 4], pot_size=40)
    bot.get_action(gs_turn)
    assert bot._pot_total == 90, f"Turn pot_total: expected 90, got {bot._pot_total}"
    assert bot._street_pot == 40, f"Turn street_pot: expected 40, got {bot._street_pot}"
    total_turn = bot._pot_total + bot._street_pot
    assert total_turn == 130, f"Turn total: expected 130, got {total_turn}"

    # River: board_cards=[1,2,3,4,5], pot_size=80
    gs_river = make_state(board_cards=[1, 2, 3, 4, 5], pot_size=80)
    bot.get_action(gs_river)
    assert bot._pot_total == 130, f"River pot_total: expected 130, got {bot._pot_total}"
    assert bot._street_pot == 80, f"River street_pot: expected 80, got {bot._street_pot}"
    total_river = bot._pot_total + bot._street_pot
    assert total_river == 210, f"River total: expected 210, got {total_river}"


# --- STATE-02: Hand boundary resets ---

def test_state02_hand_boundary_resets():
    """Verify per-hand state resets when board_cards transitions from non-empty to empty."""
    bot = HawkEyeBot()

    # Play through a hand: preflop -> flop with some pot
    gs_preflop = make_state(board_cards=[], pot_size=30)
    bot.get_action(gs_preflop)

    gs_flop = make_state(board_cards=[1, 2, 3], pot_size=60)
    bot.get_action(gs_flop)
    # At this point pot_total=30, street_pot=60

    # New hand starts: board_cards goes back to []
    gs_new_hand = make_state(board_cards=[], pot_size=30)
    bot.get_action(gs_new_hand)

    # All per-hand state should be reset
    assert bot._pot_total == 0, f"Reset pot_total: expected 0, got {bot._pot_total}"
    assert bot._street_pot == 30, f"Reset street_pot: expected 30, got {bot._street_pot}"
    assert bot._was_preflop_aggressor is False, \
        f"Reset aggressor: expected False, got {bot._was_preflop_aggressor}"


# --- STATE-03: Preflop aggressor persists ---

def test_state03_preflop_aggressor_persists():
    """Verify _was_preflop_aggressor is True after raising preflop with premium hand
    and persists into flop call."""
    bot = HawkEyeBot()

    # Preflop with AA, call_amount=20 (RFI) -> bot should raise and set aggressor flag
    # Phase 2: bb_option (call_amount=0) checks; RFI (call_amount=bb) raises
    aa_cards = make_premium_cards()
    gs_preflop = make_state(board_cards=[], pot_size=30, call_amount=20,
                            hole_cards=aa_cards)
    result = bot.get_action(gs_preflop)
    assert result[0] == "raise", f"Expected raise, got {result[0]}"
    assert bot._was_preflop_aggressor is True, \
        f"Aggressor after raise: expected True, got {bot._was_preflop_aggressor}"

    # Move to flop -- aggressor flag should persist
    gs_flop = make_state(board_cards=[1, 2, 3], pot_size=60, call_amount=0)
    bot.get_action(gs_flop)
    assert bot._was_preflop_aggressor is True, \
        f"Aggressor on flop: expected True, got {bot._was_preflop_aggressor}"


# --- STATE-04: Hand counter increments ---

def test_state04_hand_counter_increments():
    """Verify hand counter increments across 3 hand transitions (1, 2, 3)."""
    bot = HawkEyeBot()

    # Hand 1: preflop
    gs = make_state(board_cards=[], pot_size=30)
    bot.get_action(gs)
    assert bot._hand_num == 1, f"Hand 1: expected 1, got {bot._hand_num}"

    # Move to flop (still hand 1)
    gs_flop = make_state(board_cards=[1, 2, 3], pot_size=60)
    bot.get_action(gs_flop)
    assert bot._hand_num == 1, f"Still hand 1: expected 1, got {bot._hand_num}"

    # Hand 2: board goes back to empty
    gs_hand2 = make_state(board_cards=[], pot_size=30)
    bot.get_action(gs_hand2)
    assert bot._hand_num == 2, f"Hand 2: expected 2, got {bot._hand_num}"

    # Move to river (still hand 2)
    gs_river = make_state(board_cards=[1, 2, 3, 4, 5], pot_size=80)
    bot.get_action(gs_river)
    assert bot._hand_num == 2, f"Still hand 2: expected 2, got {bot._hand_num}"

    # Hand 3: board goes back to empty
    gs_hand3 = make_state(board_cards=[], pot_size=30)
    bot.get_action(gs_hand3)
    assert bot._hand_num == 3, f"Hand 3: expected 3, got {bot._hand_num}"


# --- First-hand sentinel edge case ---

def test_first_hand_sentinel():
    """Verify first-hand edge case: _last_board_len starts at -1,
    first call with board_cards=[] correctly sets _hand_num=1."""
    bot = HawkEyeBot()

    # Before any calls, sentinel should be -1
    assert bot._last_board_len == -1, \
        f"Initial sentinel: expected -1, got {bot._last_board_len}"

    # First call with empty board
    gs = make_state(board_cards=[], pot_size=30)
    bot.get_action(gs)

    assert bot._hand_num == 1, f"First hand: expected 1, got {bot._hand_num}"
    assert bot._last_board_len == 0, \
        f"After first call board_len: expected 0, got {bot._last_board_len}"


# --- Same-street idempotency ---

def test_same_street_no_double_count():
    """Verify multiple calls within same street do not re-accumulate pot."""
    bot = HawkEyeBot()

    # Preflop call 1: pot_size=30
    gs1 = make_state(board_cards=[], pot_size=30)
    bot.get_action(gs1)
    assert bot._pot_total == 0, f"Call 1 pot_total: expected 0, got {bot._pot_total}"
    assert bot._street_pot == 30, f"Call 1 street_pot: expected 30, got {bot._street_pot}"

    # Preflop call 2: pot_size=50 (same street, pot grew from more betting)
    gs2 = make_state(board_cards=[], pot_size=50)
    bot.get_action(gs2)
    assert bot._pot_total == 0, \
        f"Call 2 pot_total: expected 0 (no street transition), got {bot._pot_total}"
    assert bot._street_pot == 50, f"Call 2 street_pot: expected 50, got {bot._street_pot}"


# --- Main runner (for environments without pytest) ---

if __name__ == "__main__":
    tests = [
        test_state01_pot_accumulator_across_streets,
        test_state02_hand_boundary_resets,
        test_state03_preflop_aggressor_persists,
        test_state04_hand_counter_increments,
        test_first_hand_sentinel,
        test_same_street_no_double_count,
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
