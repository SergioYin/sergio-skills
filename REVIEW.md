# REVIEW

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
