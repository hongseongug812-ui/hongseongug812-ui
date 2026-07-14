# CLAUDE.md — Auto Profile Curator 작업 지침

> GitHub 사용자명 하나로 공개 저장소를 분석해 GitHub 프로필 README(헤더 SVG, 기술 스택, 대표 프로젝트, 언어 비율, 커밋 기반 펫 컬렉션)를 자동 생성·갱신하는 프로젝트.
> 목적: 토큰/외부 API 키 없이도 동작하는 완전 자동화된 "살아있는" 프로필 README 제공.

## 1. 파이프라인 개요

`config.yml`의 `profile.github_username` 하나만으로 아래 순서가 실행됩니다.

```
GitHub 사용자명
  → fetch_repos.py      (공개 프로필·저장소 수집 → repos.json)
  → score_projects.py   (역할/기술 추론 + 대표 프로젝트 점수화 → curated.json)
  → render_header.py    (header.svg)
  → render_pet.py       (pet.svg, 누적 커밋 100회마다 새 공룡)
  → render_svg.py       (languages.svg)
  → render_readme.py    (templates/readme.md.j2 → README.md)
```

- GitHub Actions(`update-readme.yml`)가 매시간 17분에 실행, 변경 있을 때만 커밋.
- `test.yml`은 PR/`main` push마다 `python -m unittest discover -s tests`.

## 2. 유의사항 (절대 규칙)

- `config.yml`의 필드명 / 구조 임의 변경 금지 — 빈 값은 자동 분석으로 채워지는 설계이므로 필드를 지우거나 이름을 바꾸면 템플릿 사용자 전체가 깨짐.
- **비어 있는 값을 자동 분석 결과로 채우는 오버라이드 우선순위**(사용자가 `config.yml`에 직접 입력한 값 > 저장소 분석 결과) 를 스크립트 수정 시 유지할 것.
- 토큰/시크릿(`GITHUB_TOKEN`, `ANTHROPIC_API_KEY`, `DISCORD_WEBHOOK_URL`)을 코드·문서·커밋에 직접 적지 않는다. 항상 저장소 Secret 또는 환경 변수로만 참조.
- 핵심 파이프라인은 유료 서비스 없이 동작해야 함 (`CONTRIBUTING.md` 원칙). 기본 LLM 요약은 Ollama 로컬 모델(`qwen2.5:3b-instruct`)이며, `llm.provider: cloud`는 선택 사항으로만 유지.
- 대표 프로젝트 선정 로직(`score_projects.py`)에서 포크·보관 저장소는 계속 제외 대상으로 유지.
- 생성된 산출물(`preview/`, `.cache/`, 개인 README 내용)을 템플릿 저장소 자체에 커밋하지 않는다.
- 스크립트나 템플릿 수정 시 관련 유닛 테스트(`tests/test_score_projects.py`, `tests/test_render_pet.py` 등)를 추가·갱신.

## 3. 작업 방식

1. 스크립트 수정 전 관련 스크립트 1개 파일 단위로 범위를 좁혀 진행 (`scripts/*.py` 각각 단일 책임).
2. 변경 후 `python -m unittest discover -s tests -v`로 검증. 전체 파이프라인 수동 실행은 필요할 때만:
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   python scripts/fetch_repos.py --username <user> --output .cache/repos.json
   python scripts/score_projects.py --input .cache/repos.json --output .cache/curated.json
   python scripts/render_header.py --config config.yml --input .cache/curated.json --output preview/assets/header.svg
   python scripts/render_pet.py --input .cache/curated.json --output preview/assets/pet.svg
   python scripts/render_svg.py --input .cache/curated.json --output preview/assets/languages.svg
   python scripts/render_readme.py --input .cache/curated.json --output preview/README.md
   ```
3. GitHub Actions 워크플로(`update-readme.yml`, `test.yml`) 수정 시 `permissions: contents: write`, `concurrency` 그룹, 실패 시 `notify_on_fail.py` 알림 흐름을 그대로 유지.

## 4. 참고 문서

- 설정 가이드: `docs/SETUP.md`
- 기여 가이드: `CONTRIBUTING.md`
