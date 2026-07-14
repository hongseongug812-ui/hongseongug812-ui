"""Rank repositories with transparent, configurable quantitative rules."""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

def load_config(path: str = "config.yml") -> dict:
    import yaml

    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def days_since(iso_date: str | None, now: datetime) -> int:
    if not iso_date:
        return 10_000
    return max(0, (now - datetime.fromisoformat(iso_date.replace("Z", "+00:00"))).days)


def calculate_score(repo: dict, weights: dict, now: datetime | None = None) -> int:
    """Score a repository; forks and archived repos receive a hard exclusion penalty."""
    now = now or datetime.now(UTC)
    recent = weights["recent_commit"]
    age = days_since(repo.get("last_commit_at"), now)
    recency = recent["within_30_days"] if age <= 30 else recent["within_90_days"] if age <= 90 else recent["older"]
    diversity = min(len(repo.get("languages", [])), weights["diversity_cap"])
    score = repo.get("stars", 0) * weights["star"] + repo.get("forks", 0) * weights["fork"]
    score += recency + (weights["readme"] if repo.get("has_readme") else 0) + diversity
    score += weights.get("description", 0) if repo.get("description") else 0
    if repo.get("is_fork"):
        score -= 100
    if repo.get("is_archived"):
        score -= 100
    return score


def select_repositories(repositories: list[dict], config: dict, now: datetime | None = None) -> list[dict]:
    weights = config["selection"]["weights"]
    candidates = [repo for repo in repositories if not repo.get("is_fork") and not repo.get("is_archived")]
    for repo in candidates:
        repo["score"] = calculate_score(repo, weights, now)
    return sorted(candidates, key=lambda repo: (repo["score"], repo.get("last_commit_at") or ""), reverse=True)[: config["selection"]["top_n"]]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=".cache/repos.json")
    parser.add_argument("--output", default=".cache/curated.json")
    parser.add_argument("--config", default="config.yml")
    args = parser.parse_args()
    source = json.loads(Path(args.input).read_text(encoding="utf-8"))
    curated = select_repositories(source["repositories"], load_config(args.config))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({
        "username": source["username"],
        "profile": source.get("profile", {}),
        "repositories": curated,
        "all_repositories": source["repositories"],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Selected {len(curated)} repositories.")


if __name__ == "__main__":
    main()
