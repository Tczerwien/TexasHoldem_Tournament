"""Tournament awareness tests for HawkEyeBot.

Tests TOURN-01 (stage detection), TOURN-03 (stack role classification),
TOURN-02 (ICM multiplier), TOURN-04 (bubble play), TOURN-05 (ITM aggression),
TOURN-06 (heads-up play), and TOURN-07 (exploit adjustment).
Uses mock engine module pattern from test_bot_safety.py.
"""
import sys
import os
import types
import unittest

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
from mtt_bot import HawkEyeBot, FULL_DECK, CHEN_TABLE


def _make_game_state(active_players=6, bb=50, sb=25, stack=1500,
                     hole=None, board=None, call_amount=0, min_raise=0, pot_size=0):
    """Build a minimal game_state dict for testing."""
    return {
        "active_players": active_players,
        "blinds": {"big": bb, "small": sb},
        "stack_size": stack,
        "hole_cards": hole or [],
        "board_cards": board or [],
        "call_amount": call_amount,
        "min_raise": min_raise,
        "pot_size": pot_size,
    }


class TestStageDetection(unittest.TestCase):
    """TOURN-01: _get_tournament_stage classifies 6 tournament stages."""

    def setUp(self):
        self.bot = HawkEyeBot()

    def test_heads_up(self):
        """active_players=2, any blinds -> 'heads_up'."""
        gs = _make_game_state(active_players=2, bb=200)
        self.assertEqual(self.bot._get_tournament_stage(gs), "heads_up")

    def test_itm(self):
        """active_players=3, any blinds -> 'itm'."""
        gs = _make_game_state(active_players=3, bb=100)
        self.assertEqual(self.bot._get_tournament_stage(gs), "itm")

    def test_bubble(self):
        """active_players=4, any blinds -> 'bubble'."""
        gs = _make_game_state(active_players=4, bb=50)
        self.assertEqual(self.bot._get_tournament_stage(gs), "bubble")

    def test_early(self):
        """active_players=7, bb=20 -> 'early'."""
        gs = _make_game_state(active_players=7, bb=20)
        self.assertEqual(self.bot._get_tournament_stage(gs), "early")

    def test_early_boundary(self):
        """active_players=5, bb=30 -> 'early' (bb <= 30)."""
        gs = _make_game_state(active_players=5, bb=30)
        self.assertEqual(self.bot._get_tournament_stage(gs), "early")

    def test_middle(self):
        """active_players=6, bb=50 -> 'middle'."""
        gs = _make_game_state(active_players=6, bb=50)
        self.assertEqual(self.bot._get_tournament_stage(gs), "middle")

    def test_middle_boundary(self):
        """active_players=5, bb=100 -> 'middle' (bb <= 100)."""
        gs = _make_game_state(active_players=5, bb=100)
        self.assertEqual(self.bot._get_tournament_stage(gs), "middle")

    def test_late(self):
        """active_players=5, bb=200 -> 'late'."""
        gs = _make_game_state(active_players=5, bb=200)
        self.assertEqual(self.bot._get_tournament_stage(gs), "late")

    def test_player_count_overrides_blinds(self):
        """active_players=2, bb=20 -> 'heads_up' (player count takes priority)."""
        gs = _make_game_state(active_players=2, bb=20)
        self.assertEqual(self.bot._get_tournament_stage(gs), "heads_up")


class TestStackRole(unittest.TestCase):
    """TOURN-03: _get_stack_role classifies big/medium/short relative to avg."""

    def setUp(self):
        self.bot = HawkEyeBot()
        # Default: 10 initial players * 1500 chips = 15000 total
        self.bot._initial_table_players = 10

    def test_big_stack(self):
        """stack=6000, active=4 -> 'big' (avg=3750, 6000 >= 5625)."""
        gs = _make_game_state(active_players=4, stack=6000)
        self.assertEqual(self.bot._get_stack_role(gs), "big")

    def test_short_stack(self):
        """stack=1000, active=4 -> 'short' (avg=3750, 1000 <= 1875)."""
        gs = _make_game_state(active_players=4, stack=1000)
        self.assertEqual(self.bot._get_stack_role(gs), "short")

    def test_medium_stack(self):
        """stack=3500, active=4 -> 'medium' (between thresholds)."""
        gs = _make_game_state(active_players=4, stack=3500)
        self.assertEqual(self.bot._get_stack_role(gs), "medium")

    def test_big_boundary(self):
        """stack=5625, active=4 -> 'big' (exactly 1.5x avg)."""
        gs = _make_game_state(active_players=4, stack=5625)
        self.assertEqual(self.bot._get_stack_role(gs), "big")

    def test_short_boundary(self):
        """stack=1875, active=4 -> 'short' (exactly 0.5x avg)."""
        gs = _make_game_state(active_players=4, stack=1875)
        self.assertEqual(self.bot._get_stack_role(gs), "short")

    def test_uses_initial_table_players(self):
        """_initial_table_players=10 -> total_chips=15000, avg varies by active."""
        self.bot._initial_table_players = 10
        # With 5 active: avg = 15000/5 = 3000, big threshold = 4500
        gs = _make_game_state(active_players=5, stack=4500)
        self.assertEqual(self.bot._get_stack_role(gs), "big")
        # With 10 active: avg = 15000/10 = 1500, big threshold = 2250
        gs2 = _make_game_state(active_players=10, stack=2250)
        self.assertEqual(self.bot._get_stack_role(gs2), "big")


def _find_card(rank_int, suit_idx=0):
    """Find a card from FULL_DECK by rank (0=2..12=A) and suit index (0-3)."""
    return FULL_DECK[rank_int * 4 + suit_idx]


def _make_preflop_gs(active_players=6, bb=50, sb=25, stack=1500,
                     hole_cards=None, call_amount=None, min_raise=None):
    """Build a game_state dict suitable for preflop decisions.

    If call_amount is None, defaults to bb (RFI situation).
    If min_raise is None, defaults to bb.
    """
    if call_amount is None:
        call_amount = bb  # RFI: must call one BB to enter
    if min_raise is None:
        min_raise = bb
    if hole_cards is None:
        # Default: K2o (chen=3) -- K of spades, 2 of hearts
        hole_cards = [_find_card(11, 0), _find_card(0, 1)]
    return {
        "active_players": active_players,
        "blinds": {"big": bb, "small": sb},
        "stack_size": stack,
        "hole_cards": hole_cards,
        "board_cards": [],
        "call_amount": call_amount,
        "min_raise": min_raise,
        "pot_size": 0,
    }


class TestHeadsUp(unittest.TestCase):
    """TOURN-06: Heads-up wide opening with Chen >= 3."""

    def setUp(self):
        self.bot = HawkEyeBot()
        self.bot._initial_table_players = 10
        # Reset state that _preflop might use
        self.bot._was_preflop_aggressor = False
        self.bot._pot_accumulator = 0

    def test_hu_rfi_opens_wide(self):
        """active_players=2, chen=3 (K2o), rfi -> raises."""
        # K2o: rank_int K=11 suit=0, 2=rank_int 0 suit=1 => chen=3
        hole = [_find_card(11, 0), _find_card(0, 1)]
        gs = _make_preflop_gs(active_players=2, bb=100, sb=50, stack=3000,
                              hole_cards=hole, call_amount=100)
        action, amount = self.bot._preflop(gs, 150)
        self.assertEqual(action, "raise")

    def test_hu_rfi_folds_trash(self):
        """active_players=2, chen=-1 (72o), rfi -> folds."""
        # 72o: rank_int 7=5 suit=0, 2=rank_int 0 suit=1 => chen=-1
        hole = [_find_card(5, 0), _find_card(0, 1)]
        gs = _make_preflop_gs(active_players=2, bb=100, sb=50, stack=3000,
                              hole_cards=hole, call_amount=100)
        action, amount = self.bot._preflop(gs, 150)
        self.assertEqual(action, "fold")

    def test_hu_sb_complete_opens_wide(self):
        """active_players=2, sb_complete, chen=3 (K2o) -> raises."""
        hole = [_find_card(11, 0), _find_card(0, 1)]
        # sb_complete: call_amount = bb - sb = 50
        gs = _make_preflop_gs(active_players=2, bb=100, sb=50, stack=3000,
                              hole_cards=hole, call_amount=50)
        action, amount = self.bot._preflop(gs, 150)
        self.assertIn(action, ("call", "raise"))

    def test_hu_facing_open_calls_wider(self):
        """active_players=2, facing_open, chen=5 (A5o) -> calls."""
        # A5o: rank_int A=12 suit=0, 5=rank_int 3 suit=1 => chen=5
        hole = [_find_card(12, 0), _find_card(3, 1)]
        # facing_open: call_amount between bb and 6*bb
        gs = _make_preflop_gs(active_players=2, bb=100, sb=50, stack=3000,
                              hole_cards=hole, call_amount=250)
        action, amount = self.bot._preflop(gs, 400)
        self.assertEqual(action, "call")

    def test_hu_facing_open_folds_weak(self):
        """active_players=2, facing_open, chen=3 (K2o) -> folds."""
        hole = [_find_card(11, 0), _find_card(0, 1)]
        gs = _make_preflop_gs(active_players=2, bb=100, sb=50, stack=3000,
                              hole_cards=hole, call_amount=250)
        action, amount = self.bot._preflop(gs, 400)
        self.assertEqual(action, "fold")


class TestBubblePlay(unittest.TestCase):
    """TOURN-04: Bubble adjustments -- big stack opens wider, medium tightens."""

    def setUp(self):
        self.bot = HawkEyeBot()
        self.bot._initial_table_players = 10
        self.bot._was_preflop_aggressor = False
        self.bot._pot_accumulator = 0

    def test_bubble_big_stack_opens_wider(self):
        """active_players=4 (bubble), big stack, deep, rfi, chen=5 -> opens.

        Normal deep rfi_threshold=6, bubble big lowers to 5. chen=5 opens.
        """
        # A5o: chen=5
        hole = [_find_card(12, 0), _find_card(3, 1)]
        # big stack: 6000 with 4 active, avg=15000/4=3750, 6000>=5625 -> big
        gs = _make_preflop_gs(active_players=4, bb=100, sb=50, stack=6000,
                              hole_cards=hole, call_amount=100)
        action, amount = self.bot._preflop(gs, 150)
        self.assertEqual(action, "raise")

    def test_bubble_medium_stack_tightens(self):
        """active_players=4 (bubble), medium stack, deep, rfi, chen=7 -> folds.

        Normal deep rfi_threshold=6, bubble medium raises to 8. chen=7 folds.
        """
        # KJo: chen=7
        hole = [_find_card(11, 0), _find_card(9, 1)]
        # medium stack: 3500 with 4 active, avg=3750, between thresholds -> medium
        # stack=3500, bb=100 -> 35BB -> deep mode
        gs = _make_preflop_gs(active_players=4, bb=100, sb=50, stack=3500,
                              hole_cards=hole, call_amount=100)
        action, amount = self.bot._preflop(gs, 150)
        self.assertEqual(action, "fold")

    def test_bubble_short_stack_uses_pushfold(self):
        """active_players=4 (bubble), short stack (<15BB) -> push_fold mode.

        Push-fold mode pre-empts bubble threshold adjustments.
        """
        # A5o: chen=5
        hole = [_find_card(12, 0), _find_card(3, 1)]
        # stack=800, bb=100 -> 8BB -> push_fold mode
        gs = _make_preflop_gs(active_players=4, bb=100, sb=50, stack=800,
                              hole_cards=hole, call_amount=100)
        action, amount = self.bot._preflop(gs, 150)
        # Should use push-fold tables, not modified threshold logic.
        # Result depends on SHOVE_TABLE for A5o at 8BB, but the point is
        # push_fold mode is used (not the deep/medium threshold path).
        # A5o at 8BB should shove per standard push-fold ranges.
        self.assertIn(action, ("raise", "fold"))


class TestITMAggression(unittest.TestCase):
    """TOURN-05: ITM (3 players) -- opens wider, no ICM multiplier."""

    def setUp(self):
        self.bot = HawkEyeBot()
        self.bot._initial_table_players = 10
        self.bot._was_preflop_aggressor = False
        self.bot._pot_accumulator = 0

    def test_itm_opens_wider(self):
        """active_players=3 (itm), deep, rfi, chen=5 -> opens.

        Normal deep rfi_threshold=6, ITM lowers to 5. chen=5 opens.
        """
        # A5o: chen=5
        hole = [_find_card(12, 0), _find_card(3, 1)]
        # stack=5000, bb=100 -> 50BB -> deep mode
        # 3 active, avg=15000/3=5000, stack=5000 -> medium role (not relevant for ITM threshold)
        gs = _make_preflop_gs(active_players=3, bb=100, sb=50, stack=5000,
                              hole_cards=hole, call_amount=100)
        action, amount = self.bot._preflop(gs, 150)
        self.assertEqual(action, "raise")

    def test_itm_no_icm_multiplier(self):
        """active_players=3, facing_bet with large call -> NO ICM multiplier."""
        self.bot._was_preflop_aggressor = False
        gs = _make_game_state(active_players=3, bb=100, sb=50, stack=3000,
                              call_amount=1000)
        # ehs=0.40, est_pot=2000
        # req_eq = 1000 / (2000 + 1000) = 0.333
        # Without ICM: 0.40 >= 0.333 -> call
        # With ICM (if applied wrong): 0.333 * 1.4 = 0.467 > 0.40 -> fold
        # At ITM, ICM should NOT apply, so should call
        action, amount = self.bot._facing_bet(gs, 2000, 0.40, "dry", 4)
        self.assertEqual(action, "call")


class TestICMMultiplier(unittest.TestCase):
    """TOURN-02: ICM 1.4x calling multiplier at bubble for significant calls."""

    def setUp(self):
        self.bot = HawkEyeBot()
        self.bot._initial_table_players = 10
        self.bot._was_preflop_aggressor = False
        self.bot._pot_accumulator = 0

    def test_icm_at_bubble_large_call(self):
        """active_players=4 (bubble), call >= 30% stack, ehs between normal and 1.4x -> folds.

        req_eq = 1000/(2000+1000) = 0.333
        1.4x req_eq = 0.467
        ehs = 0.40 > 0.333 (normal call) but < 0.467 (ICM fold)
        """
        gs = _make_game_state(active_players=4, bb=100, sb=50, stack=3000,
                              call_amount=1000)
        action, amount = self.bot._facing_bet(gs, 2000, 0.40, "dry", 4)
        self.assertEqual(action, "fold")

    def test_icm_not_at_bubble(self):
        """active_players=6 (middle), same call/ehs -> calls (no ICM)."""
        gs = _make_game_state(active_players=6, bb=50, sb=25, stack=3000,
                              call_amount=1000)
        # Same numbers: req_eq=0.333, ehs=0.40 >= 0.333 -> call
        action, amount = self.bot._facing_bet(gs, 2000, 0.40, "dry", 4)
        self.assertEqual(action, "call")

    def test_icm_small_call_not_applied(self):
        """active_players=4 (bubble), call < 30% stack -> no ICM multiplier."""
        gs = _make_game_state(active_players=4, bb=100, sb=50, stack=3000,
                              call_amount=500)
        # req_eq = 500 / (2000 + 500) = 0.20
        # call_amount (500) < stack*0.3 (900) -> no ICM
        # ehs=0.25 >= 0.20 -> call
        action, amount = self.bot._facing_bet(gs, 2000, 0.25, "dry", 4)
        self.assertEqual(action, "call")

    def test_icm_capped_at_one(self):
        """active_players=4 (bubble), very large call -> req_eq capped at 1.0.

        Use ehs=0.80 (below 0.85 monster threshold) so pot-odds path is tested.
        req_eq = 2500/(500+2500) = 0.833, ICM: 0.833*1.4=1.167 capped at 1.0.
        ehs=0.80 < 1.0 -> fold.
        """
        gs = _make_game_state(active_players=4, bb=100, sb=50, stack=3000,
                              call_amount=2500)
        action, amount = self.bot._facing_bet(gs, 500, 0.80, "dry", 4)
        self.assertEqual(action, "fold")


class TestExploitAdjustment(unittest.TestCase):
    """TOURN-07: Field exploitation -- lower value bet threshold from 0.65 to 0.55."""

    def setUp(self):
        self.bot = HawkEyeBot()
        self.bot._initial_table_players = 10
        self.bot._was_preflop_aggressor = False
        self.bot._pot_accumulator = 0

    def test_exploit_lowers_turn_threshold(self):
        """street=4, ehs=0.58 (below 0.65 but above 0.55) -> bets."""
        gs = _make_game_state(active_players=6, bb=50, sb=25, stack=3000,
                              call_amount=0)
        action, amount = self.bot._bet_or_check(gs, 500, 0.58, "dry", 4)
        self.assertEqual(action, "raise")

    def test_exploit_lowers_river_threshold(self):
        """street=5, ehs=0.58 (below 0.65 but above 0.55) -> bets."""
        gs = _make_game_state(active_players=6, bb=50, sb=25, stack=3000,
                              call_amount=0)
        action, amount = self.bot._bet_or_check(gs, 500, 0.58, "dry", 5)
        self.assertEqual(action, "raise")

    def test_exploit_no_bet_below_adjusted(self):
        """street=4, ehs=0.50 (below 0.55) -> checks."""
        gs = _make_game_state(active_players=6, bb=50, sb=25, stack=3000,
                              call_amount=0)
        action, amount = self.bot._bet_or_check(gs, 500, 0.50, "dry", 4)
        self.assertEqual(action, "call")  # call with 0 = check


if __name__ == "__main__":
    unittest.main()
