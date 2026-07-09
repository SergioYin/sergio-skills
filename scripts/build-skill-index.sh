#!/usr/bin/env bash
# build-skill-index.sh — generate a compact one-line-per-skill catalog for
# two-tier dynamic skill retrieval (design: docs/specs/2026-07-09-claude-code-
# env-revamp-design.md).
#
# Tier 1: Claude Code injects the output via a SessionStart hook, so every
# session sees each skill's name + hook at ~1 line of cost.
# Tier 2: on a match, the agent Reads the SKILL.md at the listed path and
# follows it as if invoked.
#
# Duplicate skill names across directories: first directory wins, so list
# the source-of-truth repo (sergio-skills) before staging areas.
#
# Usage: build-skill-index.sh [output-path]   (default ~/.claude/SKILL-INDEX.md)

set -euo pipefail

OUT="${1:-$HOME/.claude/SKILL-INDEX.md}"
DIRS=(
  "$HOME/workspace/sergio-skills/skills"
  "$HOME/.agents/skills"
  "$HOME/.claude/skills-catalog"
)
DESC_MAX=160

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

{
  echo "<skill-catalog>"
  echo "The skills below are NOT loaded in this session. If the current task"
  echo "matches one, Read the SKILL.md at its path and follow it as if the"
  echo "skill had been invoked. One line per skill: name — hook — path."
  echo ""
} > "$tmp"

seen=""
count=0
for dir in "${DIRS[@]}"; do
  [ -d "$dir" ] || continue
  for f in "$dir"/*/SKILL.md; do
    [ -f "$f" ] || continue
    name="$(basename "$(dirname "$f")")"
    case " $seen " in *" $name "*) continue ;; esac
    seen="$seen $name"
    # description: from YAML frontmatter; handles plain scalars and
    # block scalars (>- / |) by joining continuation lines until the
    # next top-level key or closing ---.
    desc="$(awk '
      /^---[ \t]*$/ { fence++; if (fence == 2) exit; next }
      fence == 1 && !found && /^description:/ {
        sub(/^description:[ \t]*[>|][-+]?[ \t]*$/, "");
        sub(/^description:[ \t]*/, "");
        if (length($0)) printf "%s ", $0;
        found = 1; next
      }
      fence == 1 && found {
        if ($0 ~ /^[A-Za-z0-9_-]+:/) exit;
        gsub(/^[ \t]+/, "");
        if (length($0)) printf "%s ", $0
      }
    ' "$f" | perl -CSD -pe "s/\s+/ /g; s/^ +| +\$//g; s/^[\"']+|[\"']+\$//g; s/^(.{$DESC_MAX}).*/\$1.../")"
    echo "- ${name} — ${desc} → ${f/#$HOME/~}"
    count=$((count + 1))
  done
done >> "$tmp"

echo "</skill-catalog>" >> "$tmp"

mv "$tmp" "$OUT"
trap - EXIT
echo "Indexed $count skills → $OUT"
