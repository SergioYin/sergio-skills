# REVIEW

## 2026-10-13 — Matt Pocock skills updated to upstream 49dd158 (v1.3.1)

Source: `mattpocock/skills`. The last install was 2026-08-18, matching upstream 9c9f36c. There are 106 upstream commits since then. No install record existed, so the install layout was reconstructed from disk.

### Layout
- **Claude:**
  - Skill copies live in `~/.claude/skills-catalog/<name>/`, flattened from the upstream `skills/<bucket>/<name>/` folders.
  - Each active skill has a symlink `~/.claude/skills/<name>` pointing at its copy.
  - `build-skill-index.sh` skips active skills, so they do not appear in SKILL-INDEX.md.
- **Codex:** real directories under `~/.codex/skills/<name>/`. Codex holds a subset of the skills, with no in-progress or misc ones.

### Local divergences to preserve on every update
- `mp-code-review` is upstream `code-review` with only the `name:` line changed, to avoid a collision with Claude Code's built-in `/code-review`. Upstream treats harness name collisions as out of scope (`.out-of-scope/harness-name-collisions.md`).
- The Codex copy of `grill-with-docs/SKILL.md` carries a skill-repair patch from 2026-09-26 (`~/.codex/skill-repair-runs/20260926-174253-grill-with-docs-portable-loading`). The patch adds a branch for hosts without a Skill tool: read `../grilling/SKILL.md` and `../domain-modeling/SKILL.md` directly. Upstream HEAD still has the pre-patch text, so the update synced only the other files in that skill.

### Changes
- Updated: all Claude copies (34) and all Codex copies (25).
- Added (Claude): `implement-spec`, `pr`, `retro`, `chief-of-staff`. `chief-of-staff` is in-progress upstream and user-invoked only, so it cannot steal triggers from 幕僚长 (grok-bot-bridge).
- Added (Codex): `implement-spec`, `pr`, `retro`.
- `grill-me` (Claude): the May real directory was replaced with a catalog copy plus a symlink.
- Removed: `resolving-merge-conflicts`, which upstream removed and did not replace.
- Removed, May 2026 installs that upstream superseded:
  - `diagnose` (renamed upstream to `diagnosing-bugs`, already installed)
  - `write-a-skill` (renamed upstream to `writing-great-skills`, then `writing-for-agents`, already installed)
- Backup of every removed or replaced directory, plus the old SKILL-INDEX: `~/.claude/backups/matt-skills-20261013/`.
- SKILL-INDEX rebuilt: 48 skills.

### Verified
- Every installed copy is identical to upstream HEAD (`diff -r`), except the two divergences above.
- No duplicate skill names in `~/.claude/skills`. Claude Code hot-reloaded the new descriptions.
- One symlink is broken: `cua-driver`, because `/Applications/CuaDriver.app` is gone. It was broken before this update and is unrelated to it.

### Breaking upstream change (pending per project)
- The domain-doc convention is now `GLOSSARY.md` / `GLOSSARY-MAP.md`, renamed from `CONTEXT.md` / `CONTEXT-MAP.md`. The updated skills only look for the new names.
- Projects still on `CONTEXT.md`: agent-interop, second-brain, qqq-dca-research, ai-glass, speech-coach, pi-bot. personal-fleet already uses `GLOSSARY.md`.
- Migration for each project: `git mv CONTEXT.md GLOSSARY.md`, then update the pointers in `AGENTS.md` and `docs/agents/domain.md`.
- game_rl was migrated on 2026-10-13. The other projects migrate when work first touches their domain docs. A "Domain glossary" rule in `~/.claude/CLAUDE.md` triggers this.

### How to update next time
1. Clone upstream.
2. For each catalog skill, `rsync -a --delete` the upstream folder `skills/*/<name>/` into the catalog. Re-apply the `mp-code-review` rename.
3. Do the same for Codex. Diff Codex `grill-with-docs/SKILL.md` against the backed-up pre-patch text first, and keep the patch if upstream is unchanged.
4. Read `CHANGELOG.md` for removals and renames.
5. Rebuild the index with `scripts/build-skill-index.sh`.

## 2026-07-09 — Claude Code env revamp, Phase 1 (Subtraction)

Spec: `docs/specs/2026-07-09-claude-code-env-revamp-design.md`

### Done
- ECC plugin disabled in `~/.claude/settings.json` (marketplace + 22MB cache kept; recovery = one-word edit).
- `rules/common/` (5 files) + `rules/typescript/` (2 files) revised: dead ECC agent references replaced with built-ins (Plan/Explore agents, /code-review, /security-review, tdd skill). Note: `rules/typescript/` exists on disk but is NOT injected into sessions — only `rules/common/` is; fixed anyway.
- 27 lark-* symlinks removed from `~/.claude/skills/` (real files in `~/.agents/skills/` untouched).
- Junk archived to `~/.claude/backups/skills-archive-20260709/`: `learned`, `book-finder-workspace`, `setup-matt-pocock-skills`.
- 12 long-tail personal skills staged in `~/.claude/skills-catalog/` (indexed, not injected).
- `scripts/build-skill-index.sh` written; generates `~/.claude/SKILL-INDEX.md` (52 skills, one line each) from sergio-skills + ~/.agents/skills + skills-catalog. SessionStart hook injects it.

### Verified
- settings.json valid (jq); ECC false; hook registered.
- Static skills: 50 → 8 (hot set 7 + cua-driver).
- Index: 52 skills, valid UTF-8, deduped (sergio-skills wins on name collision).
- lark-cli 1.0.65 still functional after symlink removal.
- Tier-2 path readable (lark-im SKILL.md).
- Pending (needs fresh session): catalog visible in context; Tier-2 retrieval actually triggers.

### Gotchas / debt
- **Index size**: ~18KB ≈ 4-6k tokens, not the ~500 estimated in spec (CJK-dense descriptions). Still ~10x smaller than full static injection. If it matters, lower `DESC_MAX` (160 → 100) or write per-skill `hook:` frontmatter overrides.
- **ECC disable side effect**: session start/end summary hooks ("Previous session summary" context) are gone. If missed, build a lightweight replacement in Phase 2.
- **lark-cli upgrades** may recreate the global symlinks in `~/.claude/skills/` — if skill count jumps back to ~35, rerun the removal and consider a lark-cli config flag (Phase 3).
- **Index freshness**: manual rebuild after adding/moving skills (`scripts/build-skill-index.sh`). Could hook into git post-commit later; YAGNI for now.
- awk frontmatter parser handles plain + block scalars; exotic YAML (flow maps) untested.

### Rollback
- `~/.claude/backups/skills-archive-20260709/`: `settings.json.bak`, `restore-lark-symlinks.sh`, archived skill dirs. Move dirs back + restore settings = full revert.

## 2026-07-09 — Codex config review + P0 fix

- Desktop app and CLI share ONE config home (`~/.codex`): config.toml, auth, skills, memories, sessions. Desktop-only parts inside the same file: `[desktop]` section + two app-managed local marketplaces. No duplicate config sources.
- P0 fixed: npm `@openai/codex` was broken (0.128.0, empty vendor binary dir → ENOENT). Reinstalled → codex-cli 0.143.0, verified `login status` reads shared auth. This also unblocks Claude Code's codex plugin (rescue agent).
- Open findings (user decision pending): 106 static skills in `~/.codex/skills` incl. buggy `hermes-*` bulk import with dupes (→ Phase 3); empty AGENTS.md (→ Phase 3 single-source generation); `/private/tmp` trusted project (security smell); quota-guard Stop hook disabled + suspicious `timeout = 18200`; 69MB logs sqlite; 13 plugins all enabled.
- Follow-up (user-approved cleanup): removed `/private/tmp` trusted project from config.toml (backup: config.toml.bak-20260709-tmp-trust; re-check after next desktop-app restart in case the running app rewrites config from memory). Quota-guard verdict corrected: `timeout=18200` is intentional headroom over the guard's 18000s max sleep, and the disabled Stop hook is sensible (avoids 5h post-turn blocking) — both left as-is. logs_2.sqlite VACUUMed 69MB → 5.4MB; table is self-pruning (9.7k live rows), no rotation needed. Plugins: all 13 confirmed in use by user, kept.
