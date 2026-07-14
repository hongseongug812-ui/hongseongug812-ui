"""Local web dashboard: edit config.yml and run the curation pipeline from a browser."""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

from jinja2 import Environment, FileSystemLoader, select_autoescape
from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config.yml"
ASSETS_DIR = ROOT / "preview" / "assets"
README_PATH = ROOT / "preview" / "README.md"

yaml = YAML()
yaml.preserve_quotes = True

PIPELINE_STEPS = [
    ("Fetch repositories", [sys.executable, "scripts/fetch_repos.py", "--output", ".cache/repos.json"]),
    ("Score projects", [sys.executable, "scripts/score_projects.py", "--input", ".cache/repos.json", "--output", ".cache/curated.json"]),
    ("Render header", [sys.executable, "scripts/render_header.py", "--input", ".cache/curated.json", "--output", "preview/assets/header.svg"]),
    ("Render languages", [sys.executable, "scripts/render_svg.py", "--input", ".cache/curated.json", "--output", "preview/assets/languages.svg"]),
    ("Render README", [sys.executable, "scripts/render_readme.py", "--input", ".cache/curated.json", "--output", "preview/README.md", "--cache", ".cache/summaries.json"]),
]

TEXT_FIELDS = ["name", "headline", "introduction", "story", "affiliation", "email", "blog_url", "github_username"]
LIST_FIELDS = ["interests", "certifications", "strengths", "current_focus"]
STACK_FIELDS = ["ai_cloud", "back_end", "front_end", "database"]


def load_config() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as handle:
        return yaml.load(handle)


def save_config(config: dict) -> None:
    with CONFIG_PATH.open("w", encoding="utf-8") as handle:
        yaml.dump(config, handle)


def split_lines(raw: str) -> list[str]:
    return [line.strip() for line in raw.splitlines() if line.strip()]


def split_commas(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def parse_activities(raw: str) -> list[dict]:
    """Parse activity blocks into year-grouped activities.

    Each activity is either one line "기간 | 제목 | 설명", or a block of up to
    three lines (제목 / 기간 / 설명) separated from the next activity by a
    blank line — whichever way someone naturally types it.
    """
    entries: list[tuple[str, str, str]] = []
    blocks = [block for block in re.split(r"\n\s*\n", raw.strip()) if block.strip()]
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        if any("|" in line for line in lines):
            for line in lines:
                if "|" not in line:
                    continue
                parts = [part.strip() for part in line.split("|")]
                period, title = parts[0], parts[1] if len(parts) > 1 else ""
                description = parts[2] if len(parts) > 2 else ""
                entries.append((title, period, description))
        else:
            title = lines[0]
            period = lines[1] if len(lines) > 1 else ""
            description = lines[2] if len(lines) > 2 else ""
            entries.append((title, period, description))

    by_year: dict[str, list[dict]] = {}
    order: list[str] = []
    for title, period, description in entries:
        if not title:
            continue
        year = period[:4] if period[:4].isdigit() else "기타"
        if year not in by_year:
            by_year[year] = []
            order.append(year)
        by_year[year].append({"title": title, "description": description, "period": period})
    return [{"year": year, "items": by_year[year]} for year in sorted(order, reverse=True)]


def format_activities(activities: list[dict]) -> str:
    blocks = []
    for group in activities:
        for item in group.get("items", []):
            blocks.append(f"{item.get('title', '')}\n{item.get('period', '')}\n{item.get('description', '')}")
    return "\n\n".join(blocks)


def apply_form(config: dict, fields: dict[str, str]) -> None:
    profile = config.setdefault("profile", {})
    for name in TEXT_FIELDS:
        profile[name] = fields.get(name, "").strip()
    for name in LIST_FIELDS:
        profile[name] = split_lines(fields.get(name, ""))

    stacks = config.setdefault("stacks", {})
    for name in STACK_FIELDS:
        stacks[name] = split_commas(fields.get(f"stack_{name}", ""))
    config["development_tools"] = split_commas(fields.get("development_tools", ""))

    llm = config.setdefault("llm", {})
    llm["provider"] = fields.get("llm_provider", "local") or "local"

    render = config.setdefault("render", {})
    theme_color = fields.get("theme_color", "").strip().lstrip("#")
    if theme_color:
        render["theme_color"] = theme_color

    config["activities"] = parse_activities(fields.get("activities", ""))


def run_pipeline() -> list[dict]:
    log = []
    for label, command in PIPELINE_STEPS:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=600)
        log.append({
            "label": label,
            "ok": result.returncode == 0,
            "output": (result.stdout + result.stderr).strip(),
        })
        if result.returncode != 0:
            break
    return log


def parse_repo_slug(remote_url: str) -> str:
    match = re.search(r"github\.com[:/](.+?)(?:\.git)?$", remote_url.strip())
    return match.group(1) if match else ""


def remote_repo_slug(remote: str = "origin") -> str:
    result = subprocess.run(["git", "remote", "get-url", remote], cwd=ROOT, capture_output=True, text=True)
    return parse_repo_slug(result.stdout) if result.returncode == 0 else ""


def deploy() -> list[dict]:
    """Commit config changes, sync with the profile repo, and trigger its refresh workflow."""
    log = []

    def run(label: str, command: list[str]) -> subprocess.CompletedProcess:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=120)
        log.append({"label": label, "ok": result.returncode == 0, "output": (result.stdout + result.stderr).strip()})
        return result

    status = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True)
    if status.stdout.strip():
        run("변경사항 스테이징", ["git", "add", "-A"])
        run("변경사항 커밋", ["git", "commit", "-m", "config: update via dashboard"])

    # The hourly workflow can push to origin between our fetch and push, so retry
    # the sync a few times before giving up (classic non-fast-forward race).
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        if run("원격 저장소 확인", ["git", "fetch", "origin", "main"]).returncode != 0:
            return log
        if run("원격 변경사항 병합", ["git", "merge", "origin/main", "--no-edit", "-X", "theirs"]).returncode != 0:
            return log
        push = run(f"프로필 저장소로 push{f' (재시도 {attempt}/{max_attempts})' if attempt > 1 else ''}", ["git", "push", "origin", "main"])
        if push.returncode == 0:
            break
        if attempt == max_attempts:
            return log

    repo_slug = remote_repo_slug("origin")
    if not repo_slug:
        log.append({"label": "GitHub Actions 실행", "ok": False, "output": "origin 저장소 주소를 확인할 수 없습니다."})
        return log
    run("GitHub Actions 워크플로 실행", ["gh", "workflow", "run", "Update profile README", "--repo", repo_slug])
    return log


def render_page(status: list[dict] | None) -> str:
    config = load_config()
    profile = config.get("profile", {})
    stacks = config.get("stacks", {})
    environment = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=select_autoescape())
    template = environment.get_template("dashboard.html")
    return template.render(
        profile=profile,
        stacks=stacks,
        development_tools=", ".join(config.get("development_tools", [])),
        llm_provider=config.get("llm", {}).get("provider", "local"),
        theme_color=config.get("render", {}).get("theme_color", "7c5cfc"),
        list_fields={name: "\n".join(profile.get(name, [])) for name in LIST_FIELDS},
        activities_text=format_activities(config.get("activities", [])),
        status=status,
        readme_exists=README_PATH.exists(),
        assets_ready=(ASSETS_DIR / "header.svg").exists(),
        cache_bust=int(time.time()),
    )


class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # quieter default logging
        pass

    def _send_html(self, body: str, status: int = 200) -> None:
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802 (stdlib method name)
        if self.path == "/" or self.path.startswith("/?"):
            self._send_html(render_page(status=None))
            return
        if self.path == "/readme":
            if README_PATH.exists():
                body = README_PATH.read_text(encoding="utf-8")
                payload = body.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            else:
                self._send_html("<p>Not generated yet.</p>", status=404)
            return
        if self.path.split("?", 1)[0].startswith("/assets/"):
            name = self.path.split("?", 1)[0].removeprefix("/assets/")
            target = (ASSETS_DIR / name).resolve()
            if target.is_file() and ASSETS_DIR.resolve() in target.parents:
                data = target.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "image/svg+xml")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(404)
                self.end_headers()
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802 (stdlib method name)
        if self.path != "/run":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8")
        fields = {key: values[0] for key, values in parse_qs(raw).items()}

        config = load_config()
        apply_form(config, fields)
        save_config(config)

        status = run_pipeline()
        if fields.get("deploy") and all(step["ok"] for step in status):
            status += deploy()
        self._send_html(render_page(status=status))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    server = ThreadingHTTPServer(("127.0.0.1", args.port), DashboardHandler)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"Auto Profile Curator dashboard running at {url}")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
