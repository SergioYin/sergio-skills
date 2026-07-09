# Claude Code Environment Revamp — Design

**Date:** 2026-07-09
**Author:** SergioYin (with Claude Code)
**Status:** Approved pending user review

## Goals

Three problems, in priority order:

1. **Slim down & de-noise** — 200+ skills visible per session (ECC plugin 100+, lark suite 24, personal ~26) bloat the system prompt and cause trigger noise.
2. **Soft conventions → hard enforcement** — CLAUDE.md rules (end-to-end validation, stop-after-2-failures, checkpoint commits) rely on model discipline; move what's enforceable into hooks.
3. **Integrate with the Hermes fleet** — unified skill repository, shared memory, and a task handoff channel between Claude Code and Hermes.

Non-goal: adding new capabilities (cron, auto-memory) — deferred until the above land.

## Route

**Route A: three serial phases**, each independently verifiable and stoppable. One phase per session.

| Phase | Name | Scope |
|-------|------|-------|
| 1 | Subtraction | Disable ECC, archive junk skills, introduce dynamic skill retrieval |
| 2 | Enforcement | Hooks in settings.json for enforceable CLAUDE.md conventions |
| 3 | Fleet integration | sergio-skills as single source of truth → memory sync → task handoff |

Rejected alternative: one-shot restructure centered on sergio-skills (larger broken-state window, batch rollback risk).

## Phase 1: Subtraction (this session)

### 1a. Disable everything-claude-code plugin

- `~/.claude/settings.json`: set `"everything-claude-code@everything-claude-code": false`.
- Keep marketplace entry and 22MB plugin cache — recovery is a one-word edit.
- **Dependent edit:** `~/.claude/rules/common/{agents,testing,performance,development-workflow}.md` reference ECC agents (planner, tdd-guide, code-reviewer, …). Minimal revision: replace ECC agent references with built-in equivalents (Plan / Explore / general-purpose); leave everything else untouched.

### 1b. Dynamic skill retrieval (two-tier, Hermes-style)

Claude Code natively injects every skill description into the system prompt. Replacement mechanism:

Directory moves first:
- Remove the 24 `lark-*` symlinks from `~/.claude/skills/` (real files in `~/.agents/skills/` untouched).
- Move long-tail personal skills out of `~/.claude/skills/` into `~/.claude/skills-catalog/` — a holding area that is indexed but not injected. Phase 3 migrates these into sergio-skills proper.

Then:

1. **Index builder** — script scans skill directories (`~/workspace/sergio-skills/skills/`, `~/.agents/skills/` lark suite, `~/.claude/skills-catalog/`) reading SKILL.md frontmatter, emits `SKILL-INDEX.md`: one line per skill — `name | one-line hook | absolute path`. ~40-60 skills ≈ 400-600 tokens. Script lives in `sergio-skills/scripts/build-skill-index.sh` (shared with Hermes in Phase 3).
2. **Tier 1 — catalog in context** — `SessionStart` hook injects `SKILL-INDEX.md` as additional context. The model sees every skill's name + hook each session; trigger reliability stays close to static injection.
3. **Tier 2 — on-demand full load** — on a catalog hit, the model `Read`s the referenced SKILL.md and follows it. Non-hit skills cost one line each, forever.

Layering:

| Tier | Contents | Context cost |
|------|----------|--------------|
| Hot set (static, `~/.claude/skills/`) | superpowers process skills + top 5-10 personal skills | unchanged |
| Catalog (1 line each) | lark suite (24) + long-tail personal skills + all future skills | ~500 tokens total |
| Cold storage | archived skills | 0 |

Failure mode: if the index file is missing or the hook fails, sessions degrade to no-catalog (hot set only) — never blocking.

Known risk: `lark-cli` upgrades may recreate the global symlinks in `~/.claude/skills/`. Verify during execution; if so, record in REVIEW.md and handle in Phase 3.

### 1c. Archive obvious junk (light audit only)

Move (not delete) to `~/.claude/backups/skills-archive-20260709/`:
- `learned/` (empty directory)
- `book-finder-workspace/` (working artifacts, not a skill)
- `setup-matt-pocock-skills/` (one-shot installer)

Deep audit of remaining personal skills deferred to Phase 3 (done while migrating into sergio-skills).

### Hot set selection (initial)

Static in `~/.claude/skills/`: `agent-reach`, `knowledge-explainer`, `skill-engineering`, `xingjian-perspective`, `diagnose`, `write-a-skill`, `grill-me`. Everything else → catalog. List adjustable at any time by moving a directory and rebuilding the index.

### Verification (Phase 1)

1. `jq . ~/.claude/settings.json` — valid JSON.
2. `ls ~/.claude/skills | wc -l` before/after.
3. `build-skill-index.sh` runs clean; `SKILL-INDEX.md` line count matches skill count.
4. `lark-cli` still functional after symlink removal (run a read-only lark command).
5. Fresh session: visible skill count drops to ~40; catalog appears in context; a catalog-only skill (e.g. `lark-im`) can be retrieved and executed via Tier 2.

### Rollback (Phase 1)

- `settings.json` backed up before edit.
- lark symlink manifest saved to the backup dir (one command recreates all).
- Archived skills are moved, not deleted — move back to restore.
- Removing the SessionStart hook restores pre-catalog behavior.

## Phase 2: Enforcement (skeleton — design in its own session)

Candidate hooks, to be validated for signal quality before enabling:

- **PostToolUse** (Edit/Write): auto-format touched files.
- **Stop**: check session for verification evidence before allowing completion claims (heuristic; advisory message, not hard block, to start).
- **PreToolUse** (Bash): guard destructive patterns beyond current deny list.
- **SessionStart**: already used for skill catalog (Phase 1); may also surface Hermes context (Phase 3).

Principle: hooks enforce what is mechanically checkable; everything else stays in CLAUDE.md as convention.

## Phase 3: Fleet integration (skeleton — design in its own session)

Order matters: repository unification is the carrier for the other two.

1. **Skill repository unification** — migrate personal skills into `sergio-skills/skills/`; both Claude Code (hot set symlinks + catalog index) and Hermes (`~/.hermes/skills` or its `external_dirs`) install from it. Deep audit of long-tail skills happens here.
2. **Memory sharing** — sync between `~/.claude/projects/*/memory/` and `~/.hermes/memories/` (USER.md as the richest profile). Direction and conflict policy TBD in Phase 3 design.
3. **Task handoff channel** — structured handoff between Claude Code and Hermes (candidate: file-based inbox under `~/workspace/system/handoff/` + Hermes cron watcher; alternatives: kanban.db, Feishu). TBD in Phase 3 design.

## Success criteria (overall)

- System prompt skill load: 200+ → ~40 visible + ~500-token catalog.
- Zero dead references in rules/ after ECC disable.
- Any cataloged skill retrievable and executable in a fresh session.
- Phases 2-3 have enough skeleton here to start their own design sessions without re-deriving context.
