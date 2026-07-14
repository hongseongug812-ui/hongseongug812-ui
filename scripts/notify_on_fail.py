"""Send an optional Discord alert without making notifications a failure point."""
from __future__ import annotations

import json
import os
import urllib.request


def main() -> None:
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook:
        print("No DISCORD_WEBHOOK_URL configured; skipping failure notification.")
        return
    repository = os.environ.get("GITHUB_REPOSITORY", "this repository")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    url = f"https://github.com/{repository}/actions/runs/{run_id}" if run_id else ""
    payload = {"content": f"⚠️ Auto Profile Curator failed for **{repository}**. {url}"}
    try:
        request = urllib.request.Request(webhook, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=15):
            pass
    except Exception as error:
        print(f"Failure notification could not be delivered: {error}")


if __name__ == "__main__":
    main()
