from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts.generate_profile import activity_svg, calculate_streak, summarise, utc_window, write_if_changed


class GenerateProfileTests(unittest.TestCase):
    def test_utc_window_is_stable_for_whole_days(self) -> None:
        start, end = utc_window(datetime(2026, 8, 7, 12, tzinfo=timezone.utc))
        self.assertEqual(start, "2025-08-08T00:00:00Z")
        self.assertEqual(end, "2026-08-07T23:59:59Z")

    def test_streaks_ignore_an_unfinished_empty_today(self) -> None:
        days = [
            {"contributionCount": 0},
            {"contributionCount": 2},
            {"contributionCount": 1},
            {"contributionCount": 0},
        ]
        self.assertEqual(calculate_streak(days), (2, 2))

    def test_summary_uses_public_repository_signals(self) -> None:
        user = {
            "followers": {"totalCount": 5},
            "contributionsCollection": {
                "contributionCalendar": {
                    "totalContributions": 3,
                    "weeks": [{"contributionDays": [{"contributionCount": 3, "date": "2026-08-07"}]}],
                }
            },
            "repositories": {
                "totalCount": 2,
                "nodes": [
                    {"stargazerCount": 2, "primaryLanguage": {"name": "Python", "color": "#3572A5"}},
                    {"stargazerCount": 1, "primaryLanguage": {"name": "Python", "color": "#3572A5"}},
                ],
            },
        }
        result = summarise(user)
        self.assertEqual(result["stars"], 3)
        self.assertEqual(result["languages"][0][:2], ("Python", 2))

    def test_svg_is_accessible_and_contains_metrics(self) -> None:
        summary = {
            "total": 42,
            "active_days": 12,
            "weekly": [1, 4, 2],
            "current_streak": 2,
            "longest_streak": 7,
            "repos": 5,
            "stars": 9,
            "followers": 3,
            "languages": [("Python", 5, "#3572A5")],
        }
        svg = activity_svg(summary)
        self.assertIn("<title", svg)
        self.assertIn("42", svg)
        self.assertIn("Python", svg)

    def test_write_if_changed_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.svg"
            self.assertTrue(write_if_changed(path, "one"))
            self.assertFalse(write_if_changed(path, "one"))


if __name__ == "__main__":
    unittest.main()

