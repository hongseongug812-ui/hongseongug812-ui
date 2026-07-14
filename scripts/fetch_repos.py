"""Collect a user's public profile and repositories using GitHub GraphQL v4."""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

API_URL = "https://api.github.com/graphql"
REST_API_URL = "https://api.github.com"
QUERY = """
query($login: String!, $after: String) {
  user(login: $login) {
    login name bio company location websiteUrl avatarUrl
    contributionsCollection { contributionYears }
    repositories(first: 100, after: $after, ownerAffiliations: OWNER, privacy: PUBLIC, orderBy: {field: UPDATED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        name nameWithOwner description url isFork isArchived stargazerCount forkCount
        primaryLanguage { name color }
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { nodes { name color } }
        defaultBranchRef {
          name
          target { ... on Commit { committedDate history(first: 1) { totalCount } } }
        }
        readme: object(expression: "HEAD:README.md") { ... on Blob { oid text } }
      }
    }
  }
}
"""
COMMIT_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) { totalCommitContributions }
  }
}
"""


def graphql(token: str, variables: dict, query: str = QUERY) -> dict:
    payload = json.dumps({"query": query, "variables": variables}).encode()
    request = urllib.request.Request(
        API_URL,
        data=payload,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "auto-profile-curator"},
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            body = json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"GitHub GraphQL failed: HTTP {exc.code}") from exc
    if body.get("errors"):
        raise RuntimeError(f"GitHub GraphQL failed: {body['errors'][0]['message']}")
    return body["data"]


def rest_get(path: str, token: str = "") -> object:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "auto-profile-curator"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{REST_API_URL}{path}", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"GitHub REST API failed: HTTP {exc.code}") from exc


def normalize(node: dict) -> dict:
    branch = node.get("defaultBranchRef") or {}
    target = branch.get("target") or {}
    readme = node.get("readme") or {}
    return {
        "name": node["name"], "full_name": node["nameWithOwner"], "url": node["url"],
        "description": node.get("description") or "", "stars": node["stargazerCount"], "forks": node["forkCount"],
        "is_fork": node["isFork"], "is_archived": node["isArchived"],
        "last_commit_at": target.get("committedDate"), "commit_count": (target.get("history") or {}).get("totalCount", 0),
        "has_readme": bool(readme), "readme_sha": readme.get("oid", ""), "readme_text": readme.get("text", ""),
        "primary_language": node.get("primaryLanguage"), "languages": node.get("languages", {}).get("nodes", []),
    }


def collect(token: str, login: str) -> tuple[dict, list[dict]]:
    after = None
    repos: list[dict] = []
    profile: dict = {}
    while True:
        data = graphql(token, {"login": login, "after": after})
        user = data.get("user")
        if not user:
            raise RuntimeError(f"GitHub user not found: {login}")
        profile = {
            "username": user["login"],
            "name": user.get("name") or "",
            "bio": user.get("bio") or "",
            "company": user.get("company") or "",
            "location": user.get("location") or "",
            "website_url": user.get("websiteUrl") or "",
            "avatar_url": user.get("avatarUrl") or "",
            "contribution_years": user.get("contributionsCollection", {}).get("contributionYears", []),
        }
        connection = user["repositories"]
        repos.extend(normalize(node) for node in connection["nodes"])
        if not connection["pageInfo"]["hasNextPage"]:
            profile["commit_count"] = collect_commit_count(token, login, profile["contribution_years"])
            return profile, repos
        after = connection["pageInfo"]["endCursor"]


def collect_commit_count(token: str, login: str, years: list[int]) -> int:
    current_year = datetime.now(UTC).year
    total = 0
    for year in years:
        end = datetime.now(UTC) if year == current_year else datetime(year + 1, 1, 1, tzinfo=UTC)
        data = graphql(token, {
            "login": login,
            "from": datetime(year, 1, 1, tzinfo=UTC).isoformat(),
            "to": end.isoformat(),
        }, COMMIT_QUERY)
        total += data["user"]["contributionsCollection"]["totalCommitContributions"]
    return total


def collect_public(login: str) -> tuple[dict, list[dict]]:
    user = rest_get(f"/users/{login}")
    nodes = rest_get(f"/users/{login}/repos?per_page=100&sort=updated&type=owner")
    profile = {
        "username": user["login"],
        "name": user.get("name") or "",
        "bio": user.get("bio") or "",
        "company": user.get("company") or "",
        "location": user.get("location") or "",
        "website_url": user.get("blog") or "",
        "avatar_url": user.get("avatar_url") or "",
        "commit_count": 0,
    }
    repos = []
    for node in nodes:
        primary = {"name": node["language"], "color": None} if node.get("language") else None
        repos.append({
            "name": node["name"], "full_name": node["full_name"], "url": node["html_url"],
            "description": node.get("description") or "", "stars": node["stargazers_count"], "forks": node["forks_count"],
            "is_fork": node["fork"], "is_archived": node["archived"],
            "last_commit_at": node.get("pushed_at"), "commit_count": 0,
            "has_readme": False, "readme_sha": "", "readme_text": "",
            "primary_language": primary, "languages": [primary] if primary else [],
        })
    return profile, repos


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=".cache/repos.json")
    parser.add_argument("--username", default="")
    parser.add_argument("--config", default="config.yml")
    args = parser.parse_args()
    token = os.environ.get("GITHUB_TOKEN", "")
    import yaml

    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    configured = config.get("profile", {}).get("github_username", "")
    username = args.username or configured or os.environ.get("GITHUB_REPOSITORY_OWNER", "")
    if not username:
        sys.exit("Set profile.github_username, pass --username, or run inside GitHub Actions.")
    profile, repos = collect(token, username) if token else collect_public(username)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"username": profile["username"], "profile": profile, "repositories": repos}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Collected {len(repos)} repositories for {profile['username']}.")


if __name__ == "__main__":
    main()
