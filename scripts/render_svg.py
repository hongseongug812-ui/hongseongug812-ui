"""Render a self-contained language distribution SVG from selected projects."""
from __future__ import annotations

import argparse
import html
import json
from collections import Counter
from pathlib import Path


def render(language_counts: Counter[str]) -> str:
    total = sum(language_counts.values()) or 1
    palette = ["#7C5CFC", "#22C55E", "#38BDF8", "#F59E0B", "#F43F5E", "#A78BFA"]
    x = 24.0
    segments = []
    labels = []
    for index, (language, count) in enumerate(language_counts.most_common(6)):
        width = count / total * 652
        color = palette[index]
        segments.append(f'<rect x="{x:.2f}" y="70" width="{width:.2f}" height="14" fill="{color}"/>')
        column = index % 3
        row = index // 3
        label_x = 28 + column * 218
        label_y = 119 + row * 28
        labels.append(
            f'<circle cx="{label_x}" cy="{label_y - 5}" r="5" fill="{color}"/>'
            f'<text x="{label_x + 13}" y="{label_y}" class="label">{html.escape(language)}</text>'
            f'<text x="{label_x + 190}" y="{label_y}" text-anchor="end" class="percent">{count / total:.0%}</text>'
        )
        x += width
    return """<svg xmlns="http://www.w3.org/2000/svg" width="700" height="178" viewBox="0 0 700 178" role="img" aria-label="Languages used across featured repositories">
<style>
  .panel { fill: #f6f8fa; stroke: #d0d7de; }
  .title { fill: #1f2328; font: 600 18px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
  .subtitle, .percent { fill: #656d76; font: 12px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
  .label { fill: #1f2328; font: 600 13px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
  @media (prefers-color-scheme: dark) {
    .panel { fill: #161b22; stroke: #30363d; }
    .title, .label { fill: #e6edf3; }
    .subtitle, .percent { fill: #8b949e; }
  }
</style>
<rect class="panel" x="0.5" y="0.5" width="699" height="177" rx="8"/>
<text x="24" y="34" class="title">Language mix</text>
<text x="24" y="53" class="subtitle">Across automatically selected repositories</text>
<clipPath id="bar"><rect x="24" y="70" width="652" height="14" rx="7"/></clipPath>
<g clip-path="url(#bar)">""" + "".join(segments) + "</g><g>" + "".join(labels) + "</g></svg>"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=".cache/curated.json")
    parser.add_argument("--output", default="assets/languages.svg")
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    languages = Counter(language["name"] for repo in data["repositories"] for language in repo.get("languages", []))
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(languages), encoding="utf-8")


if __name__ == "__main__":
    main()
