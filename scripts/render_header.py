"""Render an editorial profile header SVG from config.yml."""
from __future__ import annotations

import argparse
import html
import json
from collections import Counter
from pathlib import Path

import yaml

from render_readme import infer_role


def escape(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def render(profile: dict, accent: str, repositories: list[dict]) -> str:
    name = escape(profile.get("name", "Your Name"))
    headline = escape(profile.get("headline", "Developer"))
    username = escape(profile.get("github_username") or "github-profile")
    affiliation = escape(profile.get("affiliation"))
    interests = [escape(item) for item in profile.get("interests", [])[:3]]
    context = "  /  ".join(item for item in [affiliation, *interests] if item)
    context_svg = f'<text x="54" y="184" class="meta">{context}</text>' if context else ""
    languages = Counter(
        repo["primary_language"]["name"]
        for repo in repositories
        if repo.get("primary_language")
    )
    primary_language = escape(languages.most_common(1)[0][0] if languages else "N/A")
    latest_update = max((repo.get("last_commit_at") or "" for repo in repositories), default="")[:10] or "N/A"
    project_count = len(repositories)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="900" height="320" viewBox="0 0 900 320" role="img" aria-label="Profile header for {name}">
<style>
  .panel {{ fill: #ffffff; stroke: #d0d7de; }}
  .name {{ fill: #0d1117; font: 800 50px ui-monospace, SFMono-Regular, Menlo, monospace; letter-spacing: 0; }}
  .headline {{ fill: #424a53; font: 700 18px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; letter-spacing: 0; }}
  .meta {{ fill: #656d76; font: 13px ui-monospace, SFMono-Regular, Menlo, monospace; letter-spacing: 0; }}
  .eyebrow {{ fill: #{accent}; font: 700 12px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; letter-spacing: 0; }}
  .stat-value {{ fill: #0d1117; font: 800 21px ui-monospace, SFMono-Regular, Menlo, monospace; }}
  .stat-label {{ fill: #656d76; font: 11px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
  .pixel-dark {{ fill: #24292f; }}
  .pixel-soft {{ fill: #d8dee4; }}
  @media (prefers-color-scheme: dark) {{
    .panel {{ fill: #0d1117; stroke: #30363d; }}
    .name, .stat-value {{ fill: #f0f6fc; }}
    .headline {{ fill: #c9d1d9; }}
    .meta, .stat-label {{ fill: #8b949e; }}
    .pixel-dark {{ fill: #f0f6fc; }}
    .pixel-soft {{ fill: #30363d; }}
  }}
</style>
<rect class="panel" x="0.5" y="0.5" width="899" height="319" rx="8"/>
<rect x="0" y="0" width="10" height="320" rx="5" fill="#{accent}"/>
<text x="54" y="48" class="eyebrow">{username.upper()} / AUTO-CURATED PROFILE</text>
<text x="54" y="118" class="name">{name}<animate attributeName="opacity" values="1;0.82;1" dur="4s" repeatCount="indefinite"/></text>
<rect x="54" y="138" width="62" height="5" fill="#{accent}"/>
<text x="54" y="164" class="headline">{headline}</text>
{context_svg}
<g transform="translate(54 226)">
  <text x="0" y="18" class="stat-value">{project_count}</text><text x="0" y="39" class="stat-label">PUBLIC PROJECTS</text>
  <text x="170" y="18" class="stat-value">{primary_language}</text><text x="170" y="39" class="stat-label">PRIMARY LANGUAGE</text>
  <text x="390" y="18" class="stat-value">{latest_update}</text><text x="390" y="39" class="stat-label">LATEST UPDATE</text>
</g>
<g transform="translate(680 54)">
  <g><animateTransform attributeName="transform" type="translate" values="0 0;0 -8;0 0" dur="3s" repeatCount="indefinite"/>
    <rect x="0" y="22" width="28" height="28" fill="#{accent}"/><rect x="28" y="22" width="28" height="28" class="pixel-dark"/>
    <rect x="56" y="22" width="28" height="28" fill="#{accent}"/><rect x="28" y="50" width="28" height="28" fill="#{accent}"/>
  </g>
  <g transform="translate(82 92)"><animateTransform attributeName="transform" type="translate" additive="sum" values="0 0;10 0;0 0" dur="4s" repeatCount="indefinite"/>
    <rect width="24" height="24" class="pixel-soft"/><rect x="24" width="24" height="24" fill="#{accent}"/>
    <rect x="48" width="24" height="24" class="pixel-dark"/><rect x="24" y="24" width="24" height="24" class="pixel-dark"/>
  </g>
  <path d="M0 190H150M0 208H112M0 226H132" stroke="#{accent}" stroke-width="7"/>
</g>
</svg>"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yml")
    parser.add_argument("--input", default=".cache/curated.json")
    parser.add_argument("--output", default="assets/header.svg")
    args = parser.parse_args()
    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    github_profile = data.get("profile", {})
    profile = config.get("profile", {}).copy()
    profile["github_username"] = profile.get("github_username") or data.get("username", "")
    profile["name"] = profile.get("name") or github_profile.get("name") or data.get("username", "")
    inferred_role, _ = infer_role(data.get("all_repositories", data.get("repositories", [])))
    profile["headline"] = profile.get("headline") or inferred_role
    profile["affiliation"] = profile.get("affiliation") or github_profile.get("company") or github_profile.get("location", "")
    if not profile.get("interests"):
        profile["interests"] = list(dict.fromkeys(
            repo["primary_language"]["name"]
            for repo in data.get("repositories", [])
            if repo.get("primary_language")
        ))[:3]
    accent = str(config.get("render", {}).get("theme_color", "7c5cfc")).lstrip("#")
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(profile, accent, data.get("all_repositories", data.get("repositories", []))), encoding="utf-8")


if __name__ == "__main__":
    main()
