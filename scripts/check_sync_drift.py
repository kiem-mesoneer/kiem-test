#!/usr/bin/env python3
"""Alert if the ADR sync (Git -> Confluence, Git -> Claude plugin) is stale.

DS-273 acceptance criterion: "alert if either sync path fails or drifts >24h
behind main." This script is meant to run on a schedule (see
.github/workflows/sync-claude-plugin.yml) and compares:

  - the timestamp of the last commit touching adr/**
  - the timestamp recorded in claude-plugin/skills/adr-lookup/VERSION's
    companion .last-synced file, written by the sync workflow after a
    successful run

and exits non-zero (which the workflow turns into a Slack/webhook alert) if
the gap exceeds 24 hours, or if the plugin skill doesn't exist at all yet.
"""

import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAST_SYNCED_FILE = ROOT / "claude-plugin" / "skills" / "adr-lookup" / ".last-synced"
DRIFT_THRESHOLD = timedelta(hours=24)


def last_adr_commit_time() -> datetime:
    result = subprocess.run(
        ["git", "log", "-1", "--format=%cI", "--", "adr/"],
        cwd=ROOT, capture_output=True, text=True,
    )
    out = result.stdout.strip()
    if result.returncode != 0 or not out:
        # Empty repo, or no commits touching adr/ yet — nothing to drift-check.
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(out)


def last_synced_time() -> datetime | None:
    if not LAST_SYNCED_FILE.exists():
        return None
    return datetime.fromisoformat(LAST_SYNCED_FILE.read_text().strip())


def main() -> int:
    last_commit = last_adr_commit_time()
    last_synced = last_synced_time()

    if last_synced is None:
        print("DRIFT ALERT: claude-plugin/skills/adr-lookup has never been synced.", file=sys.stderr)
        return 1

    gap = last_commit - last_synced
    if gap > DRIFT_THRESHOLD:
        print(
            f"DRIFT ALERT: last ADR commit ({last_commit.isoformat()}) is "
            f"{gap} ahead of the last successful plugin sync ({last_synced.isoformat()}), "
            f"exceeding the {DRIFT_THRESHOLD} threshold.",
            file=sys.stderr,
        )
        return 1

    print(f"OK: plugin sync is within {DRIFT_THRESHOLD} of the last ADR commit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
