"""Preflop lookup table tests for HawkEyeBot.

Tests all precomputed tables (FULL_DECK, CHEN_TABLE, SHOVE_TABLE, CALL_TABLE)
and the _get_chen_key helper method. Covers requirements:
COMP-01, COMP-02, COMP-03, COMP-04, COMP-05, PRE-01, PRE-04, PRE-05.

Uses mock engine module to avoid import dependency on the actual engine.
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
from mtt_bot import HawkEyeBot, FULL_DECK, CHEN_TABLE, SHOVE_TABLE, CALL_TABLE, COMBO_INDICES

# Helper: build a treys card integer from rank_int (0-12) and suit_int (1,2,4,8)
_PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41]


def make_card(rank_int, suit_int):
    """Build a treys-encoded card integer.

    rank_int: 0=2, 1=3, ..., 10=Q, 11=K, 12=A
    suit_int: 1=spades, 2=hearts, 4=diamonds, 8=clubs
    """
    return (1 << rank_int << 16) | (suit_int << 12) | (rank_int << 8) | _PRIMES[rank_int]


class TestFullDeck(unittest.TestCase):
    """COMP-01: Full deck validation."""

    def test_full_deck_count(self):
        """FULL_DECK has exactly 52 entries."""
        self.assertEqual(len(FULL_DECK), 52)

    def test_full_deck_unique(self):
        """All 52 cards are unique integers."""
        self.assertEqual(len(set(FULL_DECK)), 52)

    def test_full_deck_all_integers(self):
        """Every entry is an integer."""
        for card in FULL_DECK:
            self.assertIsInstance(card, int)

    def test_full_deck_valid_ranks_and_suits(self):
        """Each card has extractable rank 0-12 and suit in {1,2,4,8}."""
        valid_suits = {1, 2, 4, 8}
        for card in FULL_DECK:
            rank = (card >> 8) & 0xF
            suit = (card >> 12) & 0xF
            self.assertGreaterEqual(rank, 0, f"Card {card}: rank {rank} < 0")
            self.assertLessEqual(rank, 12, f"Card {card}: rank {rank} > 12")
            self.assertIn(suit, valid_suits, f"Card {card}: suit {suit} not valid")


class TestChenTable(unittest.TestCase):
    """COMP-02, PRE-01: Chen formula table validation."""

    def test_chen_table_structure(self):
        """CHEN_TABLE has exactly 169 entries, all mapping to integers."""
        self.assertEqual(len(CHEN_TABLE), 169)
        for key, val in CHEN_TABLE.items():
            self.assertIsInstance(key, tuple)
            self.assertEqual(len(key), 3)
            high, low, suited = key
            self.assertIsInstance(high, int)
            self.assertIsInstance(low, int)
            self.assertIsInstance(suited, bool)
            self.assertGreaterEqual(high, low, f"Key {key}: high < low")
            self.assertIsInstance(val, int)

    def test_chen_scores_known_hands(self):
        """Verify Chen scores for known hand categories."""
        # Pairs
        self.assertEqual(CHEN_TABLE[(12, 12, False)], 20, "AA should be 20")
        self.assertEqual(CHEN_TABLE[(11, 11, False)], 16, "KK should be 16")
        self.assertEqual(CHEN_TABLE[(10, 10, False)], 14, "QQ should be 14")
        self.assertEqual(CHEN_TABLE[(9, 9, False)], 12, "JJ should be 12")
        self.assertEqual(CHEN_TABLE[(8, 8, False)], 10, "TT should be 10")
        self.assertEqual(CHEN_TABLE[(0, 0, False)], 5, "22 should be 5 (pair min)")

    def test_chen_suited_bonus(self):
        """AKs score > AKo score (suited bonus of +2)."""
        aks = CHEN_TABLE[(12, 11, True)]
        ako = CHEN_TABLE[(12, 11, False)]
        self.assertGreater(aks, ako, f"AKs({aks}) should be > AKo({ako})")

    def test_chen_kicker_matters(self):
        """AKo score > A2o score (kicker matters for non-pairs)."""
        ako = CHEN_TABLE[(12, 11, False)]
        a2o = CHEN_TABLE[(12, 0, False)]
        self.assertGreater(ako, a2o, f"AKo({ako}) should be > A2o({a2o})")

    def test_chen_72o_minimal(self):
        """72o has a low/minimal Chen score."""
        score_72o = CHEN_TABLE[(5, 0, False)]
        self.assertLessEqual(score_72o, 1, f"72o score should be <= 1, got {score_72o}")

    def test_chen_no_suited_pairs(self):
        """No pair entry has suited=True (pairs cannot be suited)."""
        for key in CHEN_TABLE:
            high, low, suited = key
            if high == low:
                self.assertFalse(suited, f"Pair {key} should not be suited")


class TestShoveTable(unittest.TestCase):
    """COMP-03, PRE-04: Push-fold shove table validation."""

    def test_shove_table_structure(self):
        """SHOVE_TABLE has 169 entries, all values 0-15."""
        self.assertEqual(len(SHOVE_TABLE), 169)
        for key, val in SHOVE_TABLE.items():
            self.assertGreaterEqual(val, 0, f"{key}: value {val} < 0")
            self.assertLessEqual(val, 15, f"{key}: value {val} > 15")

    def test_shove_table_known_hands(self):
        """Verify shove depths for premium and trash hands."""
        self.assertEqual(SHOVE_TABLE[(12, 12, False)], 15, "AA always shoves")
        self.assertEqual(SHOVE_TABLE[(11, 11, False)], 15, "KK always shoves")
        self.assertEqual(SHOVE_TABLE[(10, 10, False)], 15, "QQ always shoves")
        self.assertEqual(SHOVE_TABLE[(12, 11, True)], 15, "AKs always shoves")
        self.assertEqual(SHOVE_TABLE[(5, 0, False)], 0, "72o never shoves")

    def test_shove_monotonicity_pairs(self):
        """Higher pairs should have >= shove depth than lower pairs."""
        # AA >= KK >= QQ >= ... >= 22
        for r in range(12, 0, -1):
            higher = SHOVE_TABLE[(r, r, False)]
            lower = SHOVE_TABLE[(r - 1, r - 1, False)]
            self.assertGreaterEqual(higher, lower,
                                    f"Pair({r},{r}) shove {higher} < Pair({r-1},{r-1}) shove {lower}")


class TestCallTable(unittest.TestCase):
    """COMP-04, PRE-05: Push-fold call table validation."""

    def test_call_table_structure(self):
        """CALL_TABLE has 169 entries, all values 0-15."""
        self.assertEqual(len(CALL_TABLE), 169)
        for key, val in CALL_TABLE.items():
            self.assertGreaterEqual(val, 0, f"{key}: value {val} < 0")
            self.assertLessEqual(val, 15, f"{key}: value {val} > 15")

    def test_call_table_known_hands(self):
        """AA always calls, 72o never calls."""
        self.assertEqual(CALL_TABLE[(12, 12, False)], 15, "AA always calls")
        self.assertEqual(CALL_TABLE[(5, 0, False)], 0, "72o never calls")

    def test_call_table_vs_shove(self):
        """PRE-05: Call ranges are always tighter than shove ranges."""
        for key in CALL_TABLE:
            call_val = CALL_TABLE[key]
            shove_val = SHOVE_TABLE[key]
            self.assertLessEqual(call_val, shove_val,
                                 f"{key}: call({call_val}) > shove({shove_val})")


class TestChenKeyExtraction(unittest.TestCase):
    """PRE-01: _get_chen_key method validation."""

    def setUp(self):
        self.bot = HawkEyeBot()

    def test_chen_key_aa(self):
        """AA returns (12, 12, False)."""
        ace_s = make_card(12, 1)   # Ace of spades
        ace_h = make_card(12, 2)   # Ace of hearts
        key = self.bot._get_chen_key([ace_s, ace_h])
        self.assertEqual(key, (12, 12, False))

    def test_chen_key_aks(self):
        """AKs returns (12, 11, True)."""
        ace_s = make_card(12, 1)   # Ace of spades
        king_s = make_card(11, 1)  # King of spades
        key = self.bot._get_chen_key([ace_s, king_s])
        self.assertEqual(key, (12, 11, True))

    def test_chen_key_ako(self):
        """AKo returns (12, 11, False)."""
        ace_s = make_card(12, 1)   # Ace of spades
        king_h = make_card(11, 2)  # King of hearts
        key = self.bot._get_chen_key([ace_s, king_h])
        self.assertEqual(key, (12, 11, False))

    def test_chen_key_72o(self):
        """72o returns (5, 0, False)."""
        seven_s = make_card(5, 1)  # 7 of spades (rank_int=5)
        two_h = make_card(0, 2)    # 2 of hearts (rank_int=0)
        key = self.bot._get_chen_key([seven_s, two_h])
        self.assertEqual(key, (5, 0, False))

    def test_chen_key_normalization(self):
        """Card order should not matter -- always returns (high, low, suited)."""
        ace_s = make_card(12, 1)
        king_s = make_card(11, 1)
        # AKs in both orders
        key1 = self.bot._get_chen_key([ace_s, king_s])
        key2 = self.bot._get_chen_key([king_s, ace_s])
        self.assertEqual(key1, key2, f"Order matters: {key1} != {key2}")
        self.assertEqual(key1, (12, 11, True))

    def test_chen_key_pair_not_suited(self):
        """Same-suit pair still returns suited=False (pairs cannot be suited)."""
        # Two kings, same suit (not realistic but tests the logic)
        king_s1 = make_card(11, 1)
        king_s2 = make_card(11, 1)
        key = self.bot._get_chen_key([king_s1, king_s2])
        self.assertEqual(key[2], False, "Pairs should never be suited")


class TestModuleLevelImport(unittest.TestCase):
    """COMP-05: Tables are importable at module level."""

    def test_module_level_import(self):
        """All tables can be imported directly from mtt_bot."""
        # This test succeeds if the imports at the top of this file worked
        self.assertIsNotNone(FULL_DECK)
        self.assertIsNotNone(CHEN_TABLE)
        self.assertIsNotNone(SHOVE_TABLE)
        self.assertIsNotNone(CALL_TABLE)
        self.assertIsNotNone(COMBO_INDICES)
        self.assertEqual(len(COMBO_INDICES), 21)


class TestExistingSafety(unittest.TestCase):
    """Regression: Phase 1 code still works after Phase 2 additions."""

    def test_bot_instantiation(self):
        """HawkEyeBot can be instantiated without error."""
        bot = HawkEyeBot()
        self.assertEqual(bot.name, "HawkEye")

    def test_basic_get_action(self):
        """get_action returns a valid tuple with a basic game_state."""
        bot = HawkEyeBot()
        state = {
            "hole_cards": [make_card(0, 1), make_card(5, 2)],  # 2s, 7h
            "board_cards": [],
            "pot_size": 30,
            "stack_size": 1500,
            "call_amount": 20,
            "min_raise": 20,
            "blinds": {"small": 10, "big": 20},
            "active_players": 6,
        }
        result = bot.get_action(state)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        self.assertIn(result[0], ("fold", "call", "raise"))


# === Helper: game state factory ===


def make_game_state(hole_cards, stack_size=1500, call_amount=20, min_raise=20,
                    big_blind=20, small_blind=10, board_cards=None,
                    active_players=6, pot_size=30):
    """Build a standard game_state dict for tests."""
    return {
        "hole_cards": hole_cards,
        "board_cards": board_cards if board_cards is not None else [],
        "pot_size": pot_size,
        "stack_size": stack_size,
        "call_amount": call_amount,
        "min_raise": min_raise,
        "blinds": {"big": big_blind, "small": small_blind},
        "active_players": active_players,
    }


class TestStackModeDetection(unittest.TestCase):
    """PRE-02: Stack mode boundary tests."""

    def setUp(self):
        self.bot = HawkEyeBot()

    def _gs(self, stack, bb=20):
        return make_game_state([make_card(12, 1), make_card(12, 2)],
                               stack_size=stack, big_blind=bb)

    def test_deep_at_40bb(self):
        self.assertEqual(self.bot._get_stack_mode(self._gs(800, 20)), "deep")

    def test_medium_at_25bb(self):
        self.assertEqual(self.bot._get_stack_mode(self._gs(500, 20)), "medium")

    def test_shallow_at_15bb(self):
        self.assertEqual(self.bot._get_stack_mode(self._gs(300, 20)), "shallow")

    def test_push_fold_at_14bb(self):
        self.assertEqual(self.bot._get_stack_mode(self._gs(280, 20)), "push_fold")


class TestSituationDetection(unittest.TestCase):
    """PRE-06: Situation inference tests."""

    def setUp(self):
        self.bot = HawkEyeBot()

    def test_bb_option(self):
        gs = make_game_state([make_card(0, 1), make_card(0, 2)], call_amount=0)
        self.assertEqual(self.bot._detect_situation(gs), "bb_option")

    def test_sb_complete(self):
        gs = make_game_state([make_card(0, 1), make_card(0, 2)],
                             call_amount=10, big_blind=20, small_blind=10)
        self.assertEqual(self.bot._detect_situation(gs), "sb_complete")

    def test_rfi(self):
        gs = make_game_state([make_card(0, 1), make_card(0, 2)], call_amount=20)
        self.assertEqual(self.bot._detect_situation(gs), "rfi")

    def test_facing_open(self):
        gs = make_game_state([make_card(0, 1), make_card(0, 2)], call_amount=50)
        self.assertEqual(self.bot._detect_situation(gs), "facing_open")

    def test_facing_3bet(self):
        gs = make_game_state([make_card(0, 1), make_card(0, 2)], call_amount=120)
        self.assertEqual(self.bot._detect_situation(gs), "facing_3bet")


class TestPushFoldDecisions(unittest.TestCase):
    """PRE-04, PRE-05: Push-fold mode decision tests."""

    def setUp(self):
        self.bot = HawkEyeBot()

    def test_push_fold_shove_aa(self):
        """AA at 14BB should shove all-in."""
        aa = [make_card(12, 1), make_card(12, 2)]
        gs = make_game_state(aa, stack_size=280, call_amount=20, big_blind=20)
        self.bot._detect_new_hand(gs)
        action, amount = self.bot._preflop(gs, 30)
        self.assertEqual(action, "raise")

    def test_push_fold_fold_trash(self):
        """72o at 14BB should fold."""
        trash = [make_card(5, 1), make_card(0, 2)]
        gs = make_game_state(trash, stack_size=280, call_amount=20, big_blind=20)
        self.bot._detect_new_hand(gs)
        action, _ = self.bot._preflop(gs, 30)
        self.assertEqual(action, "fold")

    def test_push_fold_bb_option_checks(self):
        """Push-fold mode, call_amount=0 (BB option) -> check."""
        hand = [make_card(5, 1), make_card(0, 2)]
        gs = make_game_state(hand, stack_size=280, call_amount=0, big_blind=20)
        self.bot._detect_new_hand(gs)
        action, amount = self.bot._preflop(gs, 30)
        self.assertEqual(action, "call")
        self.assertEqual(amount, 0)

    def test_push_fold_facing_shove_aa_stays(self):
        """AA facing a shove should call/raise (stay in)."""
        aa = [make_card(12, 1), make_card(12, 2)]
        gs = make_game_state(aa, stack_size=280, call_amount=168, big_blind=20,
                             min_raise=20)
        self.bot._detect_new_hand(gs)
        action, _ = self.bot._preflop(gs, 200)
        self.assertIn(action, ("call", "raise"))

    def test_push_fold_facing_shove_trash_folds(self):
        """72o facing a shove should fold."""
        trash = [make_card(5, 1), make_card(0, 2)]
        gs = make_game_state(trash, stack_size=280, call_amount=168, big_blind=20)
        self.bot._detect_new_hand(gs)
        action, _ = self.bot._preflop(gs, 200)
        self.assertEqual(action, "fold")


class TestDeepDecisions(unittest.TestCase):
    """PRE-03, PRE-07: Deep stack preflop decisions."""

    def setUp(self):
        self.bot = HawkEyeBot()

    def test_deep_rfi_opens_strong(self):
        """AKo at 40BB+ RFI should raise."""
        ako = [make_card(12, 1), make_card(11, 2)]  # AKo
        gs = make_game_state(ako, stack_size=1500, call_amount=20, big_blind=20)
        self.bot._detect_new_hand(gs)
        action, _ = self.bot._preflop(gs, 30)
        self.assertEqual(action, "raise")

    def test_deep_rfi_folds_trash(self):
        """72o at 40BB+ RFI should fold."""
        trash = [make_card(5, 1), make_card(0, 2)]
        gs = make_game_state(trash, stack_size=1500, call_amount=20, big_blind=20)
        self.bot._detect_new_hand(gs)
        action, _ = self.bot._preflop(gs, 30)
        self.assertEqual(action, "fold")

    def test_facing_open_3bets_with_qq(self):
        """QQ facing an open should 3-bet (raise)."""
        qq = [make_card(10, 1), make_card(10, 2)]
        gs = make_game_state(qq, stack_size=1500, call_amount=50, big_blind=20,
                             min_raise=20)
        self.bot._detect_new_hand(gs)
        action, _ = self.bot._preflop(gs, 70)
        self.assertEqual(action, "raise")

    def test_facing_3bet_4bets_with_aa(self):
        """AA facing a 3-bet should 4-bet all-in."""
        aa = [make_card(12, 1), make_card(12, 2)]
        gs = make_game_state(aa, stack_size=1500, call_amount=120, big_blind=20,
                             min_raise=20)
        self.bot._detect_new_hand(gs)
        action, amount = self.bot._preflop(gs, 170)
        self.assertEqual(action, "raise")
        self.assertEqual(amount, 1500)  # all-in

    def test_facing_3bet_folds_trash(self):
        """72o facing a 3-bet should fold."""
        trash = [make_card(5, 1), make_card(0, 2)]
        gs = make_game_state(trash, stack_size=1500, call_amount=120, big_blind=20)
        self.bot._detect_new_hand(gs)
        action, _ = self.bot._preflop(gs, 170)
        self.assertEqual(action, "fold")

    def test_bb_option_checks(self):
        """BB option (call_amount=0) should check with any hand."""
        hand = [make_card(5, 1), make_card(0, 2)]
        gs = make_game_state(hand, stack_size=1500, call_amount=0, big_blind=20)
        self.bot._detect_new_hand(gs)
        action, amount = self.bot._preflop(gs, 30)
        self.assertEqual(action, "call")
        self.assertEqual(amount, 0)

    def test_sb_complete_calls_decent(self):
        """SB complete with a decent hand (chen >= 4) should call."""
        hand = [make_card(8, 1), make_card(7, 2)]  # T9o, chen ~5
        gs = make_game_state(hand, stack_size=1500, call_amount=10,
                             big_blind=20, small_blind=10)
        self.bot._detect_new_hand(gs)
        action, _ = self.bot._preflop(gs, 30)
        self.assertEqual(action, "call")


class TestRaiseSizing(unittest.TestCase):
    """PRE-09: Raise sizing tests."""

    def setUp(self):
        self.bot = HawkEyeBot()

    def test_raise_sizing_deep(self):
        """Deep stack RFI raise amount should be ~2.5*bb - call_amount = 30."""
        gs = make_game_state([make_card(12, 1), make_card(12, 2)],
                             stack_size=1500, call_amount=20, big_blind=20)
        amount = self.bot._preflop_raise_amount(gs, "deep")
        # 2.5 * 20 = 50, minus call_amount 20 = 30
        self.assertEqual(amount, 30)

    def test_raise_sizing_medium(self):
        """Medium stack RFI raise amount should be ~2.2*bb - call_amount."""
        gs = make_game_state([make_card(12, 1), make_card(12, 2)],
                             stack_size=500, call_amount=20, big_blind=20)
        amount = self.bot._preflop_raise_amount(gs, "medium")
        # 2.2 * 20 = 44, minus call_amount 20 = 24
        self.assertEqual(amount, 24)


class TestAggressorFlag(unittest.TestCase):
    """STATE-03: Preflop aggressor flag tests."""

    def setUp(self):
        self.bot = HawkEyeBot()

    def test_aggressor_flag_set_on_raise(self):
        """After raising preflop, _was_preflop_aggressor should be True."""
        aa = [make_card(12, 1), make_card(12, 2)]
        gs = make_game_state(aa, stack_size=1500, call_amount=20, big_blind=20)
        self.bot.get_action(gs)
        self.assertTrue(self.bot._was_preflop_aggressor)

    def test_aggressor_flag_not_set_on_fold(self):
        """After folding preflop, _was_preflop_aggressor should be False."""
        trash = [make_card(5, 1), make_card(0, 2)]
        gs = make_game_state(trash, stack_size=1500, call_amount=20, big_blind=20)
        self.bot.get_action(gs)
        self.assertFalse(self.bot._was_preflop_aggressor)


if __name__ == "__main__":
    unittest.main()
