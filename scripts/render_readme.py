"""Enrich selected repositories with cached summaries and render a profile README."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from llm_provider import summarize


def fallback_summary(repo: dict) -> str:
    return repo.get("description") or "이 저장소에서 관리 중인 오픈소스 프로젝트입니다."


def enrich(repositories: list[dict], settings: dict, cache: dict) -> list[dict]:
    for repo in repositories:
        key = repo.get("readme_sha")
        if key and key in cache:
            repo["summary"] = cache[key]
            continue
        text = repo.get("readme_text", "")[: settings.get("max_readme_chars", 3500)]
        if not text:
            repo["summary"] = fallback_summary(repo)
            continue
        try:
            repo["summary"] = summarize(text, settings)
            if key:
                cache[key] = repo["summary"]
        except Exception as error:  # A profile refresh should survive a transient model failure.
            print(f"Summary fallback for {repo['name']}: {error}")
            repo["summary"] = fallback_summary(repo)
    return repositories


ROLE_SIGNALS = {
    "AI/LLM 개발자": ("ai", "llm", "agent", "gemma", "openai", "pytorch", "model", "reviewer", "automation"),
    "풀스택 개발자": ("react", "next.js", "typescript", "javascript", "web", "app", "platform", "supabase"),
    "백엔드 개발자": ("backend", "api", "server", "spring", "fastapi", "java", "kotlin"),
    "클라우드/DevOps 개발자": ("cloud", "aws", "infra", "docker", "kubernetes", "deploy"),
    "게임 개발자": ("game", "unity", "shader", "tft"),
}

ROLE_FOCUS_LABEL = {
    "AI/LLM 개발자": "AI/LLM",
    "풀스택 개발자": "풀스택",
    "백엔드 개발자": "백엔드",
    "클라우드/DevOps 개발자": "클라우드/DevOps",
    "게임 개발자": "게임",
}

TECH_SIGNALS = {
    "AI & Cloud": ("OpenAI", "LLM", "PyTorch", "Gemma", "AWS"),
    "Back-end": ("FastAPI", "Spring Boot", "Python", "Java", "Kotlin", "Node.js"),
    "Front-end": ("React", "Next.js", "TypeScript", "JavaScript", "Flutter"),
    "Database": ("Supabase", "PostgreSQL", "MySQL", "Redis", "SQL"),
}


def repository_text(repo: dict) -> str:
    return " ".join([
        repo.get("name", ""), repo.get("description", ""), repo.get("readme_text", "")[:4000]
    ]).lower()


def infer_role(repositories: list[dict]) -> tuple[str, list[str]]:
    scores = Counter()
    for repo in repositories:
        text = repository_text(repo)
        for role, keywords in ROLE_SIGNALS.items():
            scores[role] += sum(1 for keyword in keywords if keyword in text)
    role = scores.most_common(1)[0][0] if scores else "소프트웨어 개발자"
    focus = [ROLE_FOCUS_LABEL[name] for name, score in scores.most_common(3) if score > 0]
    return role, focus


def infer_stacks(repositories: list[dict]) -> dict[str, list[str]]:
    languages = {
        repo["primary_language"]["name"]
        for repo in repositories
        if repo.get("primary_language")
    }
    combined = " ".join(repository_text(repo) for repo in repositories)
    detected = {
        category: [tech for tech in technologies if tech.lower() in combined]
        for category, technologies in TECH_SIGNALS.items()
    }
    detected["Back-end"] = list(dict.fromkeys(detected["Back-end"] + [
        name for name in ["Java", "Python", "Go", "Kotlin", "C#", "Rust", "PHP", "Ruby"] if name in languages
    ]))
    detected["Front-end"] = list(dict.fromkeys(detected["Front-end"] + [
        name for name in ["JavaScript", "TypeScript", "Dart", "HTML", "CSS", "Vue"] if name in languages
    ]))
    detected["Database"] = list(dict.fromkeys(detected["Database"] + [
        name for name in ["SQL", "PLpgSQL", "TSQL"] if name in languages
    ]))
    return {
        "ai_cloud": detected["AI & Cloud"],
        "back_end": detected["Back-end"],
        "front_end": detected["Front-end"],
        "database": detected["Database"],
    }


def infer_activities(repositories: list[dict]) -> list[dict]:
    candidates = sorted(
        (
            repo for repo in repositories
            if repo.get("last_commit_at") and not repo.get("is_fork") and not repo.get("is_archived")
        ),
        key=lambda repo: repo["last_commit_at"],
        reverse=True,
    )
    by_year: dict[str, list[dict]] = defaultdict(list)
    for repo in candidates:
        by_year[repo["last_commit_at"][:4]].append(repo)
    activities = []
    for year in sorted(by_year, reverse=True)[:3]:
        items = []
        for repo in by_year[year][:4]:
            items.append({
                "title": repo["name"],
                "description": repo.get("description") or f"{(repo.get('primary_language') or {}).get('name', '소프트웨어')} 프로젝트",
                "period": f"{year}.{repo['last_commit_at'][5:7]}",
            })
        activities.append({"year": year, "items": items})
    return activities


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=".cache/curated.json")
    parser.add_argument("--output", default="README.md")
    parser.add_argument("--config", default="config.yml")
    parser.add_argument("--cache", default=".cache/summaries.json")
    args = parser.parse_args()
    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    cache_path = Path(args.cache)
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    repositories = enrich(data["repositories"], config["llm"], cache)
    all_repositories = data.get("all_repositories", repositories)
    github_profile = data.get("profile", {})
    profile = config["profile"].copy()
    profile["github_username"] = profile.get("github_username") or data["username"]
    profile["name"] = profile.get("name") or github_profile.get("name") or data["username"]
    inferred_role, inferred_focus = infer_role(all_repositories)
    profile["headline"] = profile.get("headline") or inferred_role
    profile["introduction"] = profile.get("introduction") or github_profile.get("bio", "")
    profile["affiliation"] = profile.get("affiliation") or github_profile.get("company") or github_profile.get("location", "")
    profile["blog_url"] = profile.get("blog_url") or github_profile.get("website_url", "")
    profile["avatar_url"] = github_profile.get("avatar_url", "")
    if not profile.get("interests"):
        languages = list(dict.fromkeys(
            repo["primary_language"]["name"]
            for repo in all_repositories
            if repo.get("primary_language")
        ))[:3]
        profile["interests"] = inferred_focus + languages
    if not profile.get("current_focus"):
        profile["current_focus"] = [f"{focus} 프로젝트 진행 중" for focus in inferred_focus[:2]]
    if not profile.get("strengths"):
        profile["strengths"] = [
            f"공개 저장소 {len(all_repositories)}개를 통한 실전 경험",
            f"{', '.join(profile['interests'][-3:])} 기반 제품 개발 경험",
        ]
    environment = Environment(
        loader=FileSystemLoader("templates"),
        autoescape=select_autoescape(),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    stacks = config.get("stacks", {}).copy()
    inferred_stacks = infer_stacks(all_repositories)
    for category, values in inferred_stacks.items():
        if not stacks.get(category):
            stacks[category] = values
    rendered = environment.get_template("readme.md.j2").render(
        profile=profile,
        repositories=repositories,
        stacks=stacks,
        development_tools=config.get("development_tools", []),
        activities=config.get("activities", []) or infer_activities(all_repositories),
        render=config["render"],
    )
    Path(args.output).write_text(rendered.rstrip() + "\n", encoding="utf-8")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
