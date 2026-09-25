#!/usr/bin/env python3
"""
Posts a Discord message when a scheduled Cloud Run execution fails, so a
broken run is visible instead of silently missing from the channel.

Usage (from entrypoint.sh):
    python deploy/gcp/notify_failure.py "<what failed>" <exit code>
Never raises: a failing notifier must not mask the original failure.
"""
import os
import sys

import requests


def main() -> int:
    what = sys.argv[1] if len(sys.argv) > 1 else "unknown step"
    code = sys.argv[2] if len(sys.argv) > 2 else "?"
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook:
        return 0

    execution = os.environ.get("CLOUD_RUN_EXECUTION", "local")
    attempt = os.environ.get("CLOUD_RUN_TASK_ATTEMPT", "0")
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", os.environ.get("PROJECT_ID", ""))
    region = os.environ.get("CLOUD_RUN_REGION", "us-central1")
    logs = (
        f"https://console.cloud.google.com/run/jobs/executions/details/{region}/"
        f"{execution}/logs" + (f"?project={project}" if project else "")
    )
    body = {
        "embeds": [{
            "title": "🚨 Scheduled job failed",
            "description": (
                f"**{what}**\nExit code: `{code}` | attempt {int(attempt) + 1}\n"
                f"Execution: `{execution}`\n[Open logs]({logs})"
            ),
            "color": 0xFF3333,
        }]
    }
    try:
        requests.post(webhook, json=body, timeout=10)
    except Exception as exc:  # noqa: BLE001 - must never mask the real failure
        print(f"notify_failure: could not post to Discord: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
