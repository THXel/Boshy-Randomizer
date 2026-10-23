#!/usr/bin/env bash
set -eu
cd -- "$(dirname -- "$(readlink -f -- "$0")")"
exec 8>.live-tracker.lock
flock -n 8 || exit 0
exec python3 -m PY.live_tracker --native
