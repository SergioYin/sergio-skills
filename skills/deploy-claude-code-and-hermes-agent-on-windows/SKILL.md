---
name: deploy-claude-code-and-hermes-agent-on-windows
description: Use when helping a non-expert deploy Claude Code, MiniMax Token Plan, Hermes Agent, or a Feishu/Lark Hermes gateway on Windows or WSL2, especially when they need step-by-step guidance, one-time QR scan setup, or troubleshooting.
---

# Deploy Claude Code and Hermes Agent on Windows

Use this skill to guide a human through Windows WSL2, Claude Code, MiniMax Token Plan, Hermes Agent, and Feishu/Lark gateway setup. The goal is not to teach every detail; the goal is to get the user to a working Hermes Agent they can talk to from Feishu with minimal human operations.

## Operating Principle

Separate work into two roles:

- Human: buy/prepare credentials, install Windows/WSL2 basics, scan the Feishu QR once, and paste prompts into Claude Code.
- Claude Code: inspect the machine, install dependencies, install Hermes, configure MiniMax, configure Feishu, start the gateway, and verify.

Never ask the user to paste secrets into chat. When a MiniMax Token Plan Key or Feishu secret is needed, instruct Claude Code to prompt locally or open a local editor inside WSL2.

## Source Anchors

Use these public references when details drift:

- Claude Code Windows/WSL install: `https://code.claude.com/docs/en/setup`
- MiniMax Claude Code setup: `https://platform.minimaxi.com/docs/token-plan/claude-code`
- MiniMax Hermes Agent setup: `https://platform.minimaxi.com/docs/token-plan/hermes-agent`
- Hermes Feishu/Lark setup: `https://hermes-agent.nousresearch.com/docs/user-guide/messaging/feishu`
- Hermes WSL2 guide: `https://hermes-agent.nousresearch.com/docs/user-guide/windows-wsl-quickstart`

Known MiniMax invite link from the owner:

```text
https://platform.minimaxi.com/subscribe/token-plan?code=DAQmzWdCwZ&source=link
```

## First Response Pattern

When the user says they want to install Hermes on Windows, first identify the current stage:

1. Do they already have WSL2 Ubuntu open?
2. Is Claude Code installed inside WSL2?
3. Does Claude Code `/status` show `api.minimaxi.com/anthropic` and `MiniMax-M2.7`?
4. Is Hermes installed?
5. Has Feishu scan-to-create succeeded?
6. Is `hermes gateway run` currently running?
7. Can they DM or @mention the bot in Feishu?

Ask for only the next missing output, not everything at once. Useful outputs:

```bash
wsl --list --verbose
claude --version
claude doctor
hermes doctor
hermes status
hermes gateway status
```

## Human-Only Setup Sheet

Give this to the human before they start. Keep it simple.

### 1. Buy MiniMax Token Plan

Open the invite link:

```text
https://platform.minimaxi.com/subscribe/token-plan?code=DAQmzWdCwZ&source=link
```

After purchase, find the MiniMax Token Plan Key. It is different from an ordinary pay-as-you-go API key.

### 2. Install WSL2 Ubuntu

In Windows PowerShell as Administrator:

```powershell
wsl --install
```

Reboot if Windows asks. Open Ubuntu and create the Linux username/password.

Verify from PowerShell:

```powershell
wsl --list --verbose
```

The Ubuntu distro should show `VERSION 2`.

### 3. Install Base Packages In Ubuntu

Open Ubuntu, then run:

```bash
sudo apt update
sudo apt install -y git curl ca-certificates build-essential python3 python3-venv python3-pip ffmpeg jq ripgrep unzip tmux
```

### 4. Install Claude Code Inside WSL2

Still inside Ubuntu:

```bash
curl -fsSL https://claude.ai/install.sh | bash
source ~/.bashrc
claude --version
claude doctor
```

If `claude` is not found, close Ubuntu and reopen it.

### 5. Configure Claude Code To Use MiniMax

Create or edit `~/.claude/settings.json` inside WSL2:

```bash
mkdir -p ~/.claude
nano ~/.claude/settings.json
```

Paste this, replacing only the key value:

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.minimaxi.com/anthropic",
    "ANTHROPIC_AUTH_TOKEN": "<MINIMAX_TOKEN_PLAN_KEY>",
    "API_TIMEOUT_MS": "3000000",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "ANTHROPIC_MODEL": "MiniMax-M2.7",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "MiniMax-M2.7",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "MiniMax-M2.7",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "MiniMax-M2.7"
  }
}
```

Also create or edit `~/.claude.json`:

```bash
nano ~/.claude.json
```

Use:

```json
{
  "hasCompletedOnboarding": true
}
```

Start Claude Code:

```bash
claude
```

Inside Claude Code, run:

```text
/status
/model
```

Expected: `/status` shows the MiniMax Anthropic-compatible endpoint, and `/model` shows `MiniMax-M2.7`.

### 6. Paste The Bootstrap Prompt Into Claude Code

After Claude Code works, the human should stop doing manual setup and paste the bootstrap prompt below.

## Claude Code Bootstrap Prompt

Give this prompt to the user to paste into Claude Code.

```text
You are helping me deploy Hermes Agent on Windows WSL2 Ubuntu.

Important constraints:
- I can only use MiniMax Token Plan.
- Use MiniMax-M2.7 as the default model.
- Do not ask me to paste secrets into chat. When a secret is needed, stop and tell me exactly which local file or local terminal prompt to fill.
- Configure Feishu/Lark using the scan-to-create flow if available. I should only need to scan one QR code with the Feishu mobile app during Feishu setup.
- Use WebSocket mode for Feishu so I do not need a public webhook URL.
- Do not enable cron or unattended background jobs until basic Feishu chat works.
- Prefer reversible actions and explain before changing config files.

Please execute this deployment plan:

1. Inspect the environment:
   - Confirm this is WSL2 Ubuntu.
   - Check python3, git, curl, ffmpeg, jq, ripgrep, unzip, tmux.
   - Install missing base packages with apt when needed.

2. Confirm Claude Code is already using MiniMax:
   - Check claude --version and claude doctor.
   - Ask me to run /status and /model if you cannot inspect the active TUI state.
   - If Claude Code is not configured for MiniMax-M2.7, guide me to fix ~/.claude/settings.json.

3. Install Hermes Agent:
   - Use the official install command:
     curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
   - Reload PATH.
   - Run hermes doctor and hermes status.

4. Configure Hermes model:
   - Run hermes model.
   - Select MiniMax China / mainland China endpoint when available.
   - Use the MiniMax Token Plan Key.
   - Select MiniMax-M2.7.
   - Verify hermes status shows MiniMax and MiniMax-M2.7.

5. Configure Feishu/Lark:
   - Run hermes gateway setup.
   - Select Feishu / Lark.
   - Use scan-to-create if available.
   - Ask me to scan the displayed QR code once with the Feishu mobile app.
   - Choose Feishu China unless I explicitly say Lark international.
   - Choose WebSocket mode.
   - Save credentials locally in Hermes config/env files.
   - Do not request a public webhook URL.

6. Start Feishu gateway for validation:
   - First use foreground mode: hermes gateway run
   - If WSL systemd is unreliable, use tmux:
     tmux new -s hermes 'hermes gateway run'
   - Do not set up long-running Windows Task Scheduler yet.

7. Verify from Feishu:
   - Ask me to find the created bot in Feishu.
   - Ask me to send a direct message: /status
   - If using a group, ask me to add the bot to the group and @mention it.
   - Ask me to send: 你好，请回复当前模型和 provider。

8. Acceptance report:
   - WSL2 status
   - Claude Code model endpoint status
   - Hermes install status
   - Hermes provider/model
   - Feishu app creation method
   - Gateway connection mode
   - Feishu DM result
   - Group @mention result if tested
   - Remaining manual steps, if any

If anything fails, stop and show:
- The exact command that failed
- The relevant output
- The most likely cause
- The next safe command to try
```

## One-QR Feishu Rule

For Feishu, prefer this path:

```bash
hermes gateway setup
```

Then choose `Feishu / Lark` and use scan-to-create. The human scans the displayed QR code once with the Feishu mobile app. This should create the Feishu bot app, grant the needed permissions, and save the credentials locally.

Use `websocket` mode. Do not choose webhook mode for a normal Windows laptop setup because webhook mode needs a public callback URL or tunnel.

If scan-to-create is not available or fails, be honest: the one-QR requirement was not satisfied. Fall back to manual Feishu developer console setup only after telling the user that it is no longer the one-QR path.

## Feishu Validation Contract

Do not claim Feishu is configured until all three checks pass:

1. `hermes gateway run` starts without Feishu credential errors.
2. The gateway log says Feishu/Lark WebSocket is connected or running.
3. A real Feishu message round trip works.

Minimum Feishu tests:

```text
/status
你好，请回复当前模型和 provider。
```

Group behavior: in groups Hermes usually responds only when @mentioned. If a group test fails, first check whether the bot was @mentioned, then check group policy and allowlist.

## Recommended WSL Runtime Choices

Use WSL2 Ubuntu and keep repos under the Linux filesystem, for example:

```bash
mkdir -p ~/workspace/system
```

Avoid installing Hermes under `/mnt/c/...`; it is slower and can cause permission or line-ending problems.

For the gateway in WSL, foreground mode is the first validation path:

```bash
hermes gateway run
```

For a simple persistent trial without systemd:

```bash
tmux new -s hermes 'hermes gateway run'
```

Only after Feishu works should the user consider systemd or Windows Task Scheduler.

## Troubleshooting

### Claude Code Still Uses Anthropic

Check for shell-level variables overriding settings:

```bash
env | grep ANTHROPIC
```

If `ANTHROPIC_BASE_URL` or `ANTHROPIC_AUTH_TOKEN` points somewhere else, remove those exports from `~/.bashrc`, `~/.zshrc`, or shell profile files, then reopen the terminal.

### `claude` Or `hermes` Command Not Found

Reload PATH:

```bash
source ~/.bashrc
echo "$PATH"
```

If still missing, close Ubuntu and reopen it. Do not reinstall repeatedly before checking PATH.

### Hermes Does Not Show MiniMax

Run:

```bash
hermes model
```

Add the MiniMax provider from the terminal wizard, not from `/model` inside an active chat. `/model` only switches among providers that are already configured.

### Feishu QR Flow Not Shown

Run:

```bash
hermes gateway setup
```

Confirm the user selected `Feishu / Lark`. If the wizard asks for App ID and App Secret instead of showing QR, scan-to-create is unavailable in this environment or version. Explain this clearly and proceed with manual Feishu developer-console setup only if the user agrees.

### `FEISHU_APP_ID or FEISHU_APP_SECRET not set`

The Feishu wizard did not save credentials, or Hermes is reading a different `HERMES_HOME`. Check:

```bash
echo "$HERMES_HOME"
ls -la ~/.hermes
grep -R "FEISHU_APP" ~/.hermes 2>/dev/null
```

Do not print the app secret in chat. Redact it if reporting.

### Feishu Bot Does Not Reply In A Group

Check in this order:

1. Was the bot @mentioned?
2. Does direct message work?
3. Is the group allowed by policy?
4. Is `FEISHU_GROUP_ALLOWED_CHATS` set only when needed?
5. Is `platforms.feishu.extra.group_rules` configured for an open group?

Do not set `GATEWAY_ALLOW_ALL_USERS=true` casually. If the user only needs one group, prefer a group-specific rule.

### WebSocket Disconnects

Keep the first diagnosis simple:

```bash
hermes gateway run
```

Watch the terminal for connection, credential, or permission errors. WSL sleep/resume can also break network state; restart the foreground gateway before changing credentials.

### User Sends A Screenshot Or Error

Extract the exact error text first. Then map it to one of:

- Windows/WSL install problem
- Claude Code MiniMax routing problem
- Hermes install/PATH problem
- Hermes MiniMax provider problem
- Feishu scan-to-create problem
- Feishu gateway runtime problem
- Feishu permission/group policy problem

Answer with the next one or two commands only.

## Completion Criteria

The deployment is complete only when:

- `claude doctor` is usable or Claude Code has been verified with `/status` and `/model`.
- `hermes doctor` runs.
- `hermes status` shows MiniMax / `MiniMax-M2.7`.
- `hermes gateway run` connects to Feishu in WebSocket mode.
- The user receives a real Feishu reply from the new Hermes Agent.

If only CLI works but Feishu does not, report it as "Hermes CLI installed; Feishu gateway not yet complete."
