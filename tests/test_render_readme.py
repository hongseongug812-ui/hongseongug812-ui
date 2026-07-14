import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from render_readme import infer_activities, language_badges


def repo(**overrides):
    base = {"name": "demo", "description": "", "is_fork": False, "is_archived": False, "last_commit_at": "2026-03-15T00:00:00Z", "primary_language": {"name": "Python"}}
    return base | overrides


class InferActivitiesTests(unittest.TestCase):
    def test_excludes_the_profile_repository_itself(self):
        activities = infer_activities([repo(name="octocat"), repo(name="real-project")], username="octocat")
        titles = [item["title"] for group in activities for item in group["items"]]
        self.assertEqual(titles, ["real-project"])

    def test_excludes_forks_and_archived(self):
        activities = infer_activities([repo(name="a", is_fork=True), repo(name="b", is_archived=True), repo(name="c")])
        titles = [item["title"] for group in activities for item in group["items"]]
        self.assertEqual(titles, ["c"])


class LanguageBadgesTests(unittest.TestCase):
    def test_maps_known_languages_and_dedupes(self):
        badges = language_badges(["Python", "JavaScript", "Python"])
        self.assertEqual([badge["slug"] for badge in badges], ["python", "js"])
        self.assertEqual(badges[0]["url"], "https://www.python.org/")

    def test_skips_unmapped_languages(self):
        badges = language_badges(["ShaderLab", "Python"])
        self.assertEqual([badge["slug"] for badge in badges], ["python"])

    def test_empty_when_nothing_maps(self):
        self.assertEqual(language_badges(["ShaderLab"]), [])


if __name__ == "__main__":
    unittest.main()
