"""Tournament awareness tests for HawkEyeBot.

Tests TOURN-01 (stage detection) and TOURN-03 (stack role classification).
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
from mtt_bot import HawkEyeBot


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


if __name__ == "__main__":
    unittest.main()
