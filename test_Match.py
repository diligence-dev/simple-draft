import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from TournamentBase import Match, set_now_Berlin_forced


class TestMatchInit(unittest.TestCase):
    """Tests for Match initialization"""

    def setUp(self):
        """Set up test fixtures"""
        self.berlin_tz = ZoneInfo("Europe/Berlin")
        self.test_time = datetime(2026, 2, 12, 10, 0, 0, tzinfo=self.berlin_tz)
        set_now_Berlin_forced(self.test_time)

    def tearDown(self):
        """Clean up after tests"""
        set_now_Berlin_forced(None)

    def test_match_creation_with_all_parameters(self):
        """Test creating a match with all parameters specified"""
        end_time = self.test_time + timedelta(minutes=30)
        match = Match("Alice", "Bob", 2, 1, self.test_time, end_time)

        self.assertEqual(match.p1, "Alice")
        self.assertEqual(match.p2, "Bob")
        self.assertEqual(match.p1_games_won, 2)
        self.assertEqual(match.p2_games_won, 1)
        self.assertEqual(match.t_start, self.test_time)
        self.assertEqual(match.t_end, end_time)

    def test_match_creation_with_minimal_parameters(self):
        """Test creating a match with only players specified"""
        match = Match("Alice", "Bob")

        self.assertEqual(match.p1, "Alice")
        self.assertEqual(match.p2, "Bob")
        self.assertEqual(match.p1_games_won, -1)
        self.assertEqual(match.p2_games_won, -1)
        self.assertEqual(match.t_start, self.test_time)
        self.assertIsNone(match.t_end)

    def test_match_creation_with_custom_start_time(self):
        """Test creating a match with custom start time"""
        custom_time = self.test_time + timedelta(hours=1)
        match = Match("Alice", "Bob", t_start=custom_time)

        self.assertEqual(match.t_start, custom_time)


class TestMatchModFinish(unittest.TestCase):
    """Tests for Match.mod_finish method"""

    def setUp(self):
        """Set up test fixtures"""
        self.berlin_tz = ZoneInfo("Europe/Berlin")
        self.test_time = datetime(2026, 2, 12, 10, 0, 0, tzinfo=self.berlin_tz)
        set_now_Berlin_forced(self.test_time)
        self.match = Match("Alice", "Bob", t_start=self.test_time)

    def tearDown(self):
        """Clean up after tests"""
        set_now_Berlin_forced(None)

    def test_mod_finish_valid_2_0(self):
        """Test finishing a match with valid 2-0 result"""
        result = self.match.mod_finish(2, 0)

        self.assertTrue(result)
        self.assertEqual(self.match.p1_games_won, 2)
        self.assertEqual(self.match.p2_games_won, 0)
        self.assertIsNotNone(self.match.t_end)

    def test_mod_finish_valid_1_1(self):
        """Test finishing a match with valid 1-1 result"""
        result = self.match.mod_finish(1, 1)

        self.assertTrue(result)
        self.assertEqual(self.match.p1_games_won, 1)
        self.assertEqual(self.match.p2_games_won, 1)

    def test_mod_finish_valid_0_2(self):
        """Test finishing a match with valid 0-2 result"""
        result = self.match.mod_finish(0, 2)

        self.assertTrue(result)
        self.assertEqual(self.match.p1_games_won, 0)
        self.assertEqual(self.match.p2_games_won, 2)

    def test_mod_finish_valid_2_1(self):
        """Test finishing a match with valid 2-1 result"""
        result = self.match.mod_finish(2, 1)

        self.assertTrue(result)
        self.assertEqual(self.match.p1_games_won, 2)
        self.assertEqual(self.match.p2_games_won, 1)

    def test_mod_finish_invalid_negative_games(self):
        """Test mod_finish fails with negative games won"""
        result = self.match.mod_finish(-1, 2)

        self.assertFalse(result)
        self.assertEqual(self.match.p1_games_won, -1)

    def test_mod_finish_invalid_too_many_games(self):
        """Test mod_finish fails when total games > 3"""
        result = self.match.mod_finish(2, 2)

        self.assertFalse(result)

    def test_mod_finish_invalid_both_negative(self):
        """Test mod_finish fails when both players have negative games"""
        result = self.match.mod_finish(-1, -1)

        self.assertFalse(result)

    def test_mod_finish_already_finished(self):
        """Test mod_finish fails if match is already finished"""
        self.match.mod_finish(2, 0)
        result = self.match.mod_finish(1, 1)

        self.assertTrue(result)
        # Result should be updated
        self.assertEqual(self.match.p1_games_won, 1)
        self.assertEqual(self.match.p2_games_won, 1)

    def test_mod_finish_sets_end_time(self):
        """Test that mod_finish sets the t_end timestamp"""
        self.assertIsNone(self.match.t_end)
        self.match.mod_finish(2, 0)
        self.assertIsNotNone(self.match.t_end)
        self.assertEqual(self.match.t_end, self.test_time)


class TestMatchDurationSeconds(unittest.TestCase):
    """Tests for Match.duration_seconds method"""

    def setUp(self):
        """Set up test fixtures"""
        self.berlin_tz = ZoneInfo("Europe/Berlin")
        self.test_time = datetime(2026, 2, 12, 10, 0, 0, tzinfo=self.berlin_tz)
        set_now_Berlin_forced(self.test_time)

    def tearDown(self):
        """Clean up after tests"""
        set_now_Berlin_forced(None)

    def test_duration_seconds_unfinished_match(self):
        """Test that duration_seconds returns None for unfinished match"""
        match = Match("Alice", "Bob", t_start=self.test_time)
        self.assertIsNone(match.duration_seconds())

    def test_duration_seconds_finished_match(self):
        """Test duration_seconds for a finished match"""
        end_time = self.test_time + timedelta(minutes=30)
        match = Match("Alice", "Bob", 2, 0, self.test_time, end_time)

        duration = match.duration_seconds()
        self.assertEqual(duration, 1800)  # 30 minutes = 1800 seconds

    def test_duration_seconds_short_match(self):
        """Test duration_seconds for a short match"""
        end_time = self.test_time + timedelta(seconds=10)
        match = Match("Alice", "Bob", 1, 1, self.test_time, end_time)

        duration = match.duration_seconds()
        self.assertEqual(duration, 10)

    def test_duration_seconds_instant_match(self):
        """Test duration_seconds when match ends at start time"""
        match = Match("Alice", "Bob", 2, 0, self.test_time, self.test_time)

        duration = match.duration_seconds()
        self.assertEqual(duration, 0)

    def test_duration_seconds_long_match(self):
        """Test duration_seconds for a long match"""
        end_time = self.test_time + timedelta(hours=2, minutes=15)
        match = Match("Alice", "Bob", 2, 1, self.test_time, end_time)

        duration = match.duration_seconds()
        self.assertEqual(duration, 8100)  # 2 hours 15 minutes


class TestMatchIncludes(unittest.TestCase):
    """Tests for Match.includes method"""

    def test_includes_player1(self):
        """Test includes returns True for p1"""
        match = Match("Alice", "Bob")
        self.assertTrue(match.includes("Alice"))

    def test_includes_player2(self):
        """Test includes returns True for p2"""
        match = Match("Alice", "Bob")
        self.assertTrue(match.includes("Bob"))

    def test_includes_neither_player(self):
        """Test includes returns False for player not in match"""
        match = Match("Alice", "Bob")
        self.assertFalse(match.includes("Charlie"))

    def test_includes_bye(self):
        """Test includes works with 'bye' player"""
        match = Match("Alice", "bye")
        self.assertTrue(match.includes("bye"))
        self.assertTrue(match.includes("Alice"))

    def test_includes_empty_string(self):
        """Test includes with empty string"""
        match = Match("Alice", "Bob")
        self.assertFalse(match.includes(""))

    def test_includes_case_sensitive(self):
        """Test includes is case-sensitive"""
        match = Match("Alice", "Bob")
        self.assertFalse(match.includes("alice"))
        self.assertFalse(match.includes("ALICE"))


class TestMatchIsFinished(unittest.TestCase):
    """Tests for Match.is_finished method"""

    def setUp(self):
        """Set up test fixtures"""
        self.berlin_tz = ZoneInfo("Europe/Berlin")
        self.test_time = datetime(2026, 2, 12, 10, 0, 0, tzinfo=self.berlin_tz)
        set_now_Berlin_forced(self.test_time)

    def tearDown(self):
        """Clean up after tests"""
        set_now_Berlin_forced(None)

    def test_is_finished_unfinished_match(self):
        """Test is_finished returns False for unfinished match"""
        match = Match("Alice", "Bob", t_start=self.test_time)
        self.assertFalse(match.is_finished())

    def test_is_finished_with_results_no_end_time(self):
        """Test is_finished returns False if t_end is None"""
        match = Match("Alice", "Bob", 2, 0, t_start=self.test_time)
        self.assertFalse(match.is_finished())

    def test_is_finished_properly_finished(self):
        """Test is_finished returns True for properly finished match"""
        end_time = self.test_time + timedelta(minutes=30)
        match = Match("Alice", "Bob", 2, 0, self.test_time, end_time)
        self.assertTrue(match.is_finished())

    def test_is_finished_all_valid_scores(self):
        """Test is_finished with various valid scores"""
        end_time = self.test_time + timedelta(minutes=30)

        # Test 2-0
        match = Match("Alice", "Bob", 2, 0, self.test_time, end_time)
        self.assertTrue(match.is_finished())

        # Test 1-1
        match = Match("Alice", "Bob", 1, 1, self.test_time, end_time)
        self.assertTrue(match.is_finished())

        # Test 0-2
        match = Match("Alice", "Bob", 0, 2, self.test_time, end_time)
        self.assertTrue(match.is_finished())

    def test_is_finished_invalid_negative_games(self):
        """Test is_finished returns False with negative games"""
        end_time = self.test_time + timedelta(minutes=30)
        match = Match("Alice", "Bob", -1, 2, self.test_time, end_time)
        self.assertFalse(match.is_finished())

    def test_is_finished_invalid_total_games(self):
        """Test is_finished returns False when total games > 3"""
        end_time = self.test_time + timedelta(minutes=30)
        match = Match("Alice", "Bob", 2, 2, self.test_time, end_time)
        self.assertFalse(match.is_finished())


class TestMatchIter(unittest.TestCase):
    """Tests for Match.__iter__ method"""

    def test_iter_yields_correct_values(self):
        """Test that __iter__ yields p1, p2, p1_games_won, p2_games_won"""
        match = Match("Alice", "Bob", 2, 1)
        values = list(match)

        self.assertEqual(len(values), 4)
        self.assertEqual(values[0], "Alice")
        self.assertEqual(values[1], "Bob")
        self.assertEqual(values[2], 2)
        self.assertEqual(values[3], 1)

    def test_iter_unpacking(self):
        """Test that __iter__ works with tuple unpacking"""
        match = Match("Alice", "Bob", 1, 1)
        p1, p2, p1_games, p2_games = match

        self.assertEqual(p1, "Alice")
        self.assertEqual(p2, "Bob")
        self.assertEqual(p1_games, 1)
        self.assertEqual(p2_games, 1)

    def test_iter_in_loop(self):
        """Test that __iter__ works in a for loop"""
        match = Match("Charlie", "Diana", 0, 2)
        collected = []

        for item in match:
            collected.append(item)

        self.assertEqual(collected, ["Charlie", "Diana", 0, 2])


class TestMatchEdgeCases(unittest.TestCase):
    """Tests for edge cases and special scenarios"""

    def setUp(self):
        """Set up test fixtures"""
        self.berlin_tz = ZoneInfo("Europe/Berlin")
        self.test_time = datetime(2026, 2, 12, 10, 0, 0, tzinfo=self.berlin_tz)
        set_now_Berlin_forced(self.test_time)

    def tearDown(self):
        """Clean up after tests"""
        set_now_Berlin_forced(None)

    def test_match_with_bye(self):
        """Test match creation with 'bye' player"""
        match = Match("Alice", "bye")

        self.assertEqual(match.p1, "Alice")
        self.assertEqual(match.p2, "bye")
        self.assertTrue(match.includes("bye"))
        self.assertTrue(match.includes("Alice"))

    def test_match_with_special_characters(self):
        """Test match with special characters in player names"""
        match = Match("Alice-Smith", "Bob|O'Brien")

        self.assertEqual(match.p1, "Alice-Smith")
        self.assertEqual(match.p2, "Bob|O'Brien")
        self.assertTrue(match.includes("Alice-Smith"))

    def test_match_with_numbers_in_names(self):
        """Test match with numbers in player names"""
        match = Match("Player1", "Player2")

        self.assertTrue(match.includes("Player1"))
        self.assertTrue(match.includes("Player2"))


if __name__ == "__main__":
    unittest.main()
