import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from dashboard import apply_form, format_activities, parse_activities, parse_repo_slug, split_commas, split_lines


class SplitHelperTests(unittest.TestCase):
    def test_split_lines_drops_blank_lines(self):
        self.assertEqual(split_lines("AI\n\n  Cloud \n"), ["AI", "Cloud"])

    def test_split_commas_drops_blank_items(self):
        self.assertEqual(split_commas("OpenAI, , AWS ,"), ["OpenAI", "AWS"])


class ApplyFormTests(unittest.TestCase):
    def test_blank_fields_reset_to_empty_for_auto_inference(self):
        config = {"profile": {"name": "Old Name", "headline": "Old Role"}, "stacks": {"ai_cloud": ["Stale"]}}
        apply_form(config, {"github_username": "octocat"})
        self.assertEqual(config["profile"]["name"], "")
        self.assertEqual(config["profile"]["headline"], "")
        self.assertEqual(config["stacks"]["ai_cloud"], [])
        self.assertEqual(config["profile"]["github_username"], "octocat")

    def test_list_and_stack_fields_are_parsed(self):
        config = {"profile": {}, "stacks": {}}
        apply_form(config, {
            "github_username": "octocat",
            "interests": "AI\nCloud",
            "stack_back_end": "Python, FastAPI",
        })
        self.assertEqual(config["profile"]["interests"], ["AI", "Cloud"])
        self.assertEqual(config["stacks"]["back_end"], ["Python", "FastAPI"])

    def test_theme_color_only_overrides_when_provided(self):
        config = {"profile": {}, "stacks": {}, "render": {"theme_color": "7c5cfc"}}
        apply_form(config, {"github_username": "octocat", "theme_color": ""})
        self.assertEqual(config["render"]["theme_color"], "7c5cfc")
        apply_form(config, {"github_username": "octocat", "theme_color": "#ff0000"})
        self.assertEqual(config["render"]["theme_color"], "ff0000")


class ActivitiesTests(unittest.TestCase):
    def test_parse_groups_by_year_and_sorts_years_descending(self):
        activities = parse_activities("2025.11 | 해커톤 우승 | 3일 만에 만든 AI 서비스\n2026.03 | 사이드 프로젝트 A | 설명")
        self.assertEqual([group["year"] for group in activities], ["2026", "2025"])
        self.assertEqual(activities[0]["items"][0]["title"], "사이드 프로젝트 A")

    def test_parse_skips_lines_without_a_title(self):
        self.assertEqual(parse_activities("2026.03 |  | \n\n"), [])

    def test_format_and_parse_round_trip(self):
        original = [{"year": "2026", "items": [{"title": "A", "description": "d", "period": "2026.03"}]}]
        self.assertEqual(parse_activities(format_activities(original)), original)

    def test_apply_form_falls_back_to_auto_inference_when_blank(self):
        config = {"profile": {}, "stacks": {}, "activities": [{"year": "2020", "items": []}]}
        apply_form(config, {"github_username": "octocat", "activities": ""})
        self.assertEqual(config["activities"], [])


class ParseRepoSlugTests(unittest.TestCase):
    def test_https_url(self):
        self.assertEqual(parse_repo_slug("https://github.com/octocat/hello-world.git"), "octocat/hello-world")

    def test_ssh_url(self):
        self.assertEqual(parse_repo_slug("git@github.com:octocat/hello-world.git"), "octocat/hello-world")

    def test_https_url_without_git_suffix(self):
        self.assertEqual(parse_repo_slug("https://github.com/octocat/hello-world"), "octocat/hello-world")

    def test_non_github_url_returns_empty(self):
        self.assertEqual(parse_repo_slug("https://gitlab.com/octocat/hello-world.git"), "")


if __name__ == "__main__":
    unittest.main()
