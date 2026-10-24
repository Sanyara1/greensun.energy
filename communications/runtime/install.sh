#!/bin/sh
# Install only; no services/timers enabled, no config or state replaced.
set -eu
umask 077
src=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python3 -c 'import sys,zoneinfo; assert sys.version_info >= (3,9); zoneinfo.ZoneInfo("Europe/Moscow")'
target="$HOME/gsun-pr"
config="$HOME/.config/gsun-pr"
state="$HOME/.local/share/gsun-pr"
units="$HOME/.config/systemd/user"
if [ -e "$target/factory.py" ]; then
  echo 'STOP: existing installation; use reviewed update with backup' >&2
  exit 1
fi
mkdir -p "$target" "$config" "$state/assets" "$state/plans" "$units"
for name in gsun-pr.service gsun-pr.timer gsun-pr-prepare.service gsun-pr-prepare.timer gsun-pr-bridge.service; do
  if [ -e "$units/$name" ]; then echo "STOP: existing unit $name" >&2; exit 1; fi
done
for name in factory.py bridge.py README.md; do install -m 600 "$src/$name" "$target/$name"; done
for name in gsun-pr.service gsun-pr.timer gsun-pr-prepare.service gsun-pr-prepare.timer gsun-pr-bridge.service; do
  install -m 600 "$src/$name" "$units/$name"
done
if [ ! -e "$config/runtime.env" ]; then install -m 600 "$src/runtime.env.example" "$config/runtime.env"; fi
if [ ! -e "$state/facts.json" ]; then install -m 600 "$src/facts.example.json" "$state/facts.json"; fi
if [ ! -e "$state/media.json" ]; then install -m 600 "$src/media.example.json" "$state/media.json"; fi
systemctl --user daemon-reload
printf '%s\n' 'INSTALLED_DISABLED: no services or timers started; configure before enabling.'
