from datetime import UTC, datetime, timedelta
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from score_projects import calculate_score, select_repositories


WEIGHTS = {"star": 3, "fork": 2, "readme": 5, "description": 15, "diversity_cap": 10, "recent_commit": {"within_30_days": 30, "within_90_days": 15, "older": 5}}
NOW = datetime(2026, 7, 14, tzinfo=UTC)


def repo(**overrides):
    base = {"name": "demo", "stars": 2, "forks": 1, "has_readme": True, "description": "", "languages": [{"name": "Python"}], "last_commit_at": (NOW - timedelta(days=10)).isoformat(), "is_fork": False, "is_archived": False}
    return base | overrides


class ScoringTests(unittest.TestCase):
    def test_score_combines_all_quantitative_signals(self):
        self.assertEqual(calculate_score(repo(), WEIGHTS, NOW), 6 + 2 + 5 + 1 + 30)

    def test_description_bonus_rewards_documented_repos(self):
        self.assertEqual(
            calculate_score(repo(description="What it does"), WEIGHTS, NOW),
            calculate_score(repo(), WEIGHTS, NOW) + 15,
        )

    def test_forks_and_archives_are_not_selectable(self):
        config = {"selection": {"top_n": 6, "weights": WEIGHTS}}
        selected = select_repositories([repo(name="real"), repo(name="fork", is_fork=True), repo(name="archive", is_archived=True)], config, NOW)
        self.assertEqual([item["name"] for item in selected], ["real"])

    def test_tie_breaker_prefers_more_recent_commit(self):
        config = {"selection": {"top_n": 1, "weights": WEIGHTS}}
        older = repo(name="older", last_commit_at=(NOW - timedelta(days=20)).isoformat())
        newer = repo(name="newer", last_commit_at=(NOW - timedelta(days=2)).isoformat())
        self.assertEqual(select_repositories([older, newer], config, NOW)[0]["name"], "newer")


if __name__ == "__main__":
    unittest.main()
