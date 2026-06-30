#!/bin/bash
# Best-effort cleanup of stale daily-news scheduled-task runs.
#
# Why this exists: scheduled-tasks doesn't kill its own runaway runs. If a daily-news
# firing hangs (e.g. an Anthropic / WebSearch transient error puts the model into an
# unrecoverable state), the claude process sits there forever. The next firing then
# burns its per_task_limit retry budget against the dead one. Observed in practice
# (2026-06-29..30): 4 zombie processes accumulated across two editions.
#
# How it identifies a daily-news run:
#  - scheduled-tasks launches it with `--model claude-sonnet-4-6` (pinned in SKILL
#    frontmatter — see PR #10).
#  - Interactive Claude Code sessions launch with `--resume <uuid>` (continuation) or
#    `--model default` (fresh). So `--model claude-sonnet-4-6` AND no `--resume`
#    discriminates scheduled-task runs reliably.
#  - Caveat: if you ever launch a brand-new interactive session and pin Sonnet 4.6 at
#    start (no resume), and let it idle for 3h+, it'll get killed too. In practice
#    that's vanishingly rare; tighten the threshold if it ever bites.
#
# Threshold: STALE_THRESHOLD_SEC seconds (default 10800 = 3h). A healthy run finishes
# in a few minutes; 3h is well past any legitimate workload.
#
# Run on a schedule (e.g. every 30 min) via launchd / cron. Idempotent. Sends nothing
# if nothing is stale.
set -u

STALE_THRESHOLD_SEC="${STALE_THRESHOLD_SEC:-10800}"
MATCH_MODEL="${MATCH_MODEL:---model claude-sonnet-4-6}"
LOG_FILE="${LOG_FILE:-$HOME/.cache/news/cleanup-zombies.log}"
mkdir -p "$(dirname "$LOG_FILE")"

stamp() { date +"%Y-%m-%dT%H:%M:%S%z"; }

# macOS `ps` doesn't have `etimes` (seconds); parse `etime` ("MM:SS", "HH:MM:SS",
# or "DD-HH:MM:SS") in awk.
ps -axo pid,etime,command 2>/dev/null \
  | awk -v t="$STALE_THRESHOLD_SEC" -v m="$MATCH_MODEL" '
      function to_seconds(s,   parts, d, hms, n, h, mm, sec) {
        d = 0
        if (index(s, "-") > 0) { split(s, parts, "-"); d = parts[1]+0; hms = parts[2] }
        else { hms = s }
        n = split(hms, parts, ":")
        if (n == 3) { h = parts[1]+0; mm = parts[2]+0; sec = parts[3]+0 }
        else if (n == 2) { h = 0; mm = parts[1]+0; sec = parts[2]+0 }
        else { return 0 }
        return d*86400 + h*3600 + mm*60 + sec
      }
      # Scheduled-task run = pinned model, no `--resume` (which only interactive
      # session continuations carry). Match only the actual claude binary line
      # (skip the disclaimer wrapper above it, which dies on its own once the
      # child goes away).
      index($0, m) > 0 && index($0, "/Contents/MacOS/claude") > 0 && index($0, "--resume") == 0 {
        if (to_seconds($2) >= t+0) print $1 " " $2
      }
    ' \
  | while read -r pid etime; do
      echo "$(stamp) killing stale daily-news pid=$pid etime=$etime" >> "$LOG_FILE"
      kill "$pid" 2>>"$LOG_FILE" || true
      # claude installs a signal handler — give it a beat to honor SIGTERM, then SIGKILL.
      sleep 3
      if kill -0 "$pid" 2>/dev/null; then
        echo "$(stamp) SIGTERM ignored, SIGKILL pid=$pid" >> "$LOG_FILE"
        kill -9 "$pid" 2>>"$LOG_FILE" || true
      fi
    done
