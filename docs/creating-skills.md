# Creating Skills In This Repository

Use this lightweight convention for new skills.

## Layout

```text
skills/<skill-name>/
  SKILL.md
  scripts/
  examples/
  references/
```

Only `SKILL.md` is required. Add `scripts/`, `examples/`, or `references/` when they materially improve repeatability.

## Minimum Quality Bar

- `SKILL.md` states when to use the skill, exact workflow, output contract, and failure handling.
- Local scripts accept explicit paths/options instead of hard-coding one machine.
- Any cleanup or recurring task is owned by the skill and documented inside the skill.
- If a skill has runtime dependencies, add `scripts/doctor.py`.
- If a skill has a core happy path, add `scripts/smoke_test.py`.
- If a skill writes local files, add a dry-run cleanup script or clear cleanup instructions.

## Registering A Skill

After adding a new skill directory, update:

```text
.claude-plugin/marketplace.json
README.md
```

Add the path under the plugin's `skills` list:

```json
"./skills/<skill-name>"
```

