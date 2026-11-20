#!/bin/sh
# Commit and push the append-only log this repo exists to publish.
# Called after a cycle (by the agenda row "math-slow"), so a visitor always sees the latest attempts.
# Only the data paths are staged: never `git add -A`, never a force-push.
set -eu
cd "$(dirname "$0")/.."
[ -d .git ] || { echo "sync: not a git repo" >&2; exit 1; }

git add attempts/attempts.jsonl cache problems/queue.jsonl 2>/dev/null || true
if git diff --cached --quiet; then
    echo "sync: no new attempts"
    exit 0
fi
n=$(git diff --cached --numstat | awk '{s+=$1} END {print s+0}')
git commit -q -m "cycle: +$n lines of attempts ($(date -u +%Y-%m-%dT%H:%MZ))"
git push -q origin main
echo "sync: pushed +$n lines"
