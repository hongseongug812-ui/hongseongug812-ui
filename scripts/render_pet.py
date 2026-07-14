"""Render a deterministic dinosaur collection that grows every 100 commits."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path


DINOSAURS = [
    {"name": "Mint Rex", "body": "#8be0c5", "dark": "#247f6b", "accent": "#ffb84d", "kind": "rex"},
    {"name": "Berry Tricera", "body": "#d6a6ff", "dark": "#7446a8", "accent": "#ff91a4", "kind": "tricera"},
    {"name": "Sunny Stego", "body": "#ffd66b", "dark": "#a86d00", "accent": "#ff7b54", "kind": "stego"},
    {"name": "Cloud Bronto", "body": "#9ed8ff", "dark": "#397da8", "accent": "#7c5cfc", "kind": "bronto"},
    {"name": "Peach Raptor", "body": "#ffb59e", "dark": "#a84f39", "accent": "#ffe066", "kind": "raptor"},
    {"name": "Aqua Ankylo", "body": "#7ddde3", "dark": "#247b82", "accent": "#5b8def", "kind": "ankylo"},
]


def dinosaur_collection(username: str, commits: int) -> list[dict]:
    draw_count = 1 + commits // 100
    collection = []
    available = list(range(len(DINOSAURS)))
    for draw in range(draw_count):
        if not available:
            available = list(range(len(DINOSAURS)))
        digest = hashlib.sha256(f"{username}:dino:{draw}".encode()).digest()
        choice = int.from_bytes(digest[:4], "big") % len(available)
        collection.append(DINOSAURS[available.pop(choice)])
    return collection


def species_features(dino: dict) -> str:
    body, dark, accent, kind = dino["body"], dino["dark"], dino["accent"], dino["kind"]
    if kind == "rex":
        return f'<path d="M368 152L345 115L390 123L405 82L438 119L470 77L493 124L535 109L522 158Z" fill="{accent}" stroke="{dark}" stroke-width="6"/>'
    if kind == "tricera":
        return f'<path d="M352 169Q337 102 402 84L450 112L498 84Q564 103 548 169Z" fill="{accent}" stroke="{dark}" stroke-width="7"/><path d="M380 126L355 78L407 111M520 126L545 78L493 111M450 117V69" fill="{body}" stroke="{dark}" stroke-width="7" stroke-linecap="round"/>'
    if kind == "stego":
        return f'<path d="M352 165L361 117L395 143L413 93L449 135L481 91L499 143L540 113L534 166Z" fill="{accent}" stroke="{dark}" stroke-width="6"/>'
    if kind == "bronto":
        return f'<path d="M516 177Q535 102 572 78Q603 59 620 87Q629 109 598 124Q566 138 559 199Z" fill="{body}" stroke="{dark}" stroke-width="7"/><circle cx="599" cy="91" r="5" fill="#172b27"/>'
    if kind == "raptor":
        return f'<path d="M372 149Q350 108 388 82L411 123L444 76L463 122L503 87L521 151Z" fill="{accent}" stroke="{dark}" stroke-width="6"/><path d="M552 267Q624 230 645 253Q608 260 579 302" fill="{accent}" stroke="{dark}" stroke-width="6"/>'
    return f'<path d="M359 164Q365 108 404 104L424 79L449 105L477 76L496 108Q532 113 540 164Z" fill="{accent}" stroke="{dark}" stroke-width="7"/><path d="M559 286Q637 269 651 309Q627 340 575 315" fill="{accent}" stroke="{dark}" stroke-width="7"/>'


def dinosaur_svg(dino: dict) -> str:
    body, dark = dino["body"], dino["dark"]
    return f"""{species_features(dino)}
<path d="M548 251Q642 242 620 313Q603 348 547 309" fill="{body}" stroke="{dark}" stroke-width="7"/>
<path d="M450 112C372 112 326 164 326 240C326 315 376 348 450 348C524 348 574 315 574 240C574 164 528 112 450 112Z" fill="{body}" stroke="{dark}" stroke-width="7"/>
<ellipse cx="400" cy="201" rx="29" ry="37" fill="#172b27"/><ellipse cx="491" cy="201" rx="29" ry="37" fill="#172b27"/>
<ellipse cx="391" cy="188" rx="11" ry="14" fill="#fff"/><ellipse cx="482" cy="188" rx="11" ry="14" fill="#fff"/>
<circle cx="411" cy="218" r="5" fill="#fff"/><circle cx="502" cy="218" r="5" fill="#fff"/>
<ellipse cx="366" cy="252" rx="24" ry="12" fill="#ff91a4" opacity=".72"/><ellipse cx="526" cy="252" rx="24" ry="12" fill="#ff91a4" opacity=".72"/>
<path d="M426 247Q449 270 474 247" fill="#fff" stroke="#172b27" stroke-width="6" stroke-linecap="round"/>
<circle cx="438" cy="237" r="4" fill="{dark}"/><circle cx="462" cy="237" r="4" fill="{dark}"/>
<path d="M347 268Q310 279 321 307Q331 323 357 298M553 268Q586 279 575 307Q565 323 541 298" fill="{body}" stroke="{dark}" stroke-width="7" stroke-linecap="round"/>
<ellipse cx="401" cy="342" rx="37" ry="15" fill="{dark}" opacity=".55"/><ellipse cx="499" cy="342" rx="37" ry="15" fill="{dark}" opacity=".55"/>
<path d="M365 159Q400 127 435 142" fill="none" stroke="#fff" stroke-width="10" stroke-linecap="round" opacity=".38"/>"""


def render(username: str, commits: int) -> str:
    collection = dinosaur_collection(username, commits)
    active = collection[-1]
    remaining = 100 - commits % 100 if commits % 100 else 100
    progress = 190 * (commits % 100) / 100
    username_text = html.escape(username)
    dots = "".join(
        f'<circle cx="{8 + (index % 8) * 20}" cy="{148 + (index // 8) * 18}" r="6" fill="{dino["body"]}" stroke="{dino["dark"]}" stroke-width="2"/>'
        for index, dino in enumerate(collection[:16])
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="900" height="400" viewBox="0 0 900 400" role="img" aria-label="Commit dinosaur for {username_text}">
<style>
 .panel{{fill:#fff;stroke:#d0d7de}} .title{{fill:#1f2328;font:800 24px ui-monospace,SFMono-Regular,Menlo,monospace}} .text{{fill:#656d76;font:14px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}} .strong{{fill:#1f2328;font:700 14px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}
 @media(prefers-color-scheme:dark){{.panel{{fill:#0d1117;stroke:#30363d}}.title,.strong{{fill:#f0f6fc}}.text{{fill:#8b949e}}}}
</style>
<rect class="panel" x=".5" y=".5" width="899" height="399" rx="8"/>
<text x="34" y="48" class="title">{username_text}'s commit dinosaur</text>
<text x="34" y="76" class="text">A new dinosaur is summoned for every 100 commits</text>
<ellipse cx="450" cy="350" rx="108" ry="16" fill="#8c959f" opacity=".18"/>
<g><animateTransform attributeName="transform" type="translate" values="0 0;0 -6;0 0" dur="2.8s" repeatCount="indefinite"/>{dinosaur_svg(active)}</g>
<g transform="translate(635 215)"><text class="strong" y="0">{html.escape(active['name'])}</text><text class="text" y="28">{commits} commits</text><text class="text" y="52">{len(collection)} dinos collected</text><text class="text" y="76">{remaining} commits to next</text>
<rect y="94" width="220" height="10" rx="5" fill="#d8dee4"/><rect y="94" width="{progress * 220 / 190:.1f}" height="10" rx="5" fill="{active['accent']}"/><text class="text" y="128">COLLECTION</text>{dots}</g>
</svg>"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=".cache/curated.json")
    parser.add_argument("--output", default="assets/pet.svg")
    parser.add_argument("--commits", type=int)
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    username = data.get("username", "github-user")
    commits = args.commits if args.commits is not None else data.get("profile", {}).get("commit_count", 0)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(username, commits), encoding="utf-8")


if __name__ == "__main__":
    main()
