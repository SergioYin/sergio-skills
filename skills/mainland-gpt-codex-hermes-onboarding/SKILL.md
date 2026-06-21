---
name: mainland-gpt-codex-hermes-onboarding
description: Guide a mainland-China non-expert from compliant VPN/international network setup through ChatGPT account/SMS, Codex CLI, Hermes Agent, and publishing the workflow as a GitHub Skill that another daily assistant such as 豆包 can follow.
version: 1.0.0
author: SergioYin
license: MIT
metadata:
  hermes:
    tags: [gpt, chatgpt, codex, hermes, onboarding, mainland-china, github, skill]
---

# Mainland GPT → Codex → Hermes Onboarding

## 适用场景

当用户说：

- “我是中国大陆普通用户，想从零开始用 GPT / Codex / Hermes Agent。”
- “帮我配置 VPN、注册 ChatGPT、开通 Plus/Pro、用 Codex、装 Hermes。”
- “把这个流程写成说明书 / Skill，上传 GitHub，给豆包也能照着指导。”

就加载本 Skill，按“先打通基础链路，再上工具”的顺序指导。

## 重要边界

1. **合规优先**：网络访问、支付、手机号、账号注册都要遵守当地法律、平台条款和用户所在地区要求。本 Skill 不提供规避监管、伪造身份、盗用支付、批量注册、接码平台等做法。
2. **账号安全优先**：不要让 AI 或他人代收验证码；不要把密码、短信验证码、备份码、API Key 发给任何助手。
3. **真实手机号优先**：OpenAI/ChatGPT 相关验证可能不支持中国大陆 `+86` 手机号或不稳定。建议使用本人长期控制、所在地区受支持、能正常收短信的真实手机号；不要用一次性接码平台。
4. **分层验收**：网络能访问 → ChatGPT 能登录 → Codex CLI 能工作 → Hermes CLI 能工作 → 再配置 Gateway/Skills/GitHub。

## 一页总流程

```text
准备电脑和浏览器
→ 配置合规稳定的国际网络环境（VPN/代理/公司网络/境外网络，按用户合法可用方式）
→ 注册/登录 ChatGPT
→ 通过 SMS/邮箱/支付验证并开通可用套餐
→ 安装并登录 Codex CLI
→ 安装 Hermes Agent
→ 在 Hermes 中选择 OpenAI Codex / Nous Portal / 其他 provider
→ 验证 CLI 聊天、工具、文件读写
→ 写成 Skill 目录
→ 提交到 GitHub
→ 把 GitHub 链接或 SKILL.md 原文交给豆包指导日常用户
```

---

# A. 给普通人的操作说明书

## 0. 准备清单

用户需要准备：

- 一台电脑：macOS / Windows / Linux 均可；Windows 新手优先用 PowerShell 或 WSL2。
- 一个常用邮箱：Gmail、Outlook、iCloud 等，能长期登录。
- 一个本人长期控制的手机号：用于可能出现的 SMS 验证。
- 一张可用于国际在线订阅的付款方式：国际信用卡/借记卡、Apple Pay、Google Pay、或平台当时支持的其他方式。
- 一个 GitHub 账号：用于上传 Skill。
- 基础终端工具：浏览器、终端/PowerShell、Git。

验收：

```bash
git --version
```

能显示版本即可。

---

## 1. 配置合规稳定的国际网络环境（VPN/代理）

### 1.1 选择网络方式

按合法可用优先级选择：

1. 公司/学校提供的合规国际网络；
2. 自己合法购买的 VPN 或代理服务；
3. 境外手机号/境外宽带/境外云桌面等合法方式；
4. 不建议使用来路不明的免费 VPN、共享节点、机场试用节点承载账号注册和支付。

选择标准：

- 支持电脑系统；
- 有稳定节点和客服；
- 能访问 `https://chatgpt.com`、`https://platform.openai.com`、`https://github.com`；
- 不频繁跳 IP；
- 支持 TUN/全局模式或清晰的系统代理设置；
- 支付和注册时尽量使用同一国家/地区的稳定节点，不要频繁切换地区。

### 1.2 安装和开启

通用步骤：

1. 从服务商官网下载客户端，不要从网盘/陌生群文件安装。
2. 登录账号。
3. 选择一个稳定地区节点。
4. 开启系统代理或 TUN/增强模式。
5. 浏览器打开以下网站测试：
   - `https://chatgpt.com`
   - `https://platform.openai.com`
   - `https://github.com`
   - `https://developers.openai.com/codex/cli`

### 1.3 验收网络

在终端执行：

```bash
curl -I https://chatgpt.com
curl -I https://github.com
```

看到 `HTTP/2 200`、`HTTP/2 301`、`HTTP/2 302`、`HTTP/1.1 200` 等响应都算能连通。

如果失败：

- 换一个稳定节点；
- 检查系统代理是否真的生效；
- 浏览器能打开但终端不行时，说明终端没有走代理，需要配置终端代理或启用 TUN；
- 注册、支付、SMS 环节不要频繁切换节点。

---

## 2. 注册或登录 ChatGPT，并处理 SMS

### 2.1 进入官网

打开：

```text
https://chatgpt.com
```

点击 Sign up / Log in。

推荐方式：

- 用常用邮箱注册；或
- 用 Google / Apple / Microsoft 登录。

注意：以后 Codex 和 Hermes 的 OpenAI Codex provider 最好使用同一个 ChatGPT 账号，减少权限不同步。

### 2.2 邮箱验证

1. 输入邮箱。
2. 打开邮箱收信。
3. 点击 OpenAI/ChatGPT 发来的验证链接。
4. 回到 ChatGPT 页面继续。

### 2.3 SMS 手机号验证

如果页面要求手机号：

1. 选择手机号所属国家/地区。
2. 输入本人长期控制的真实手机号。
3. 接收短信验证码。
4. 在网页填入验证码。

如果 `+86` 收不到或页面不支持：

- 不要反复高频尝试，容易触发风控；
- 不要使用接码平台、共享手机号、临时号；
- 可使用本人合法持有的境外手机号/eSIM/长期号码；
- 也可以请可信亲友用其本人长期号码协助，但账号归属、付款、恢复方式要清楚，避免未来找不回；
- 仍失败时，先开普通 ChatGPT 网页能力，Codex/Hermes 可暂时用其他 provider（OpenRouter、Google、Kimi、DeepSeek、Qwen、MiniMax、Nous Portal 等）替代。

### 2.4 开通 Plus / Pro / 可用套餐

Codex CLI 官方说明中，Codex CLI 可随 ChatGPT Plus、Pro、Business、Edu、Enterprise 等计划使用。实际可用性以用户账号页面和 OpenAI 当前规则为准。

操作：

1. 进入 ChatGPT 左下角账号菜单。
2. 找到 Upgrade / Plan / Subscription。
3. 选择 Plus 或 Pro 等计划。
4. 使用可支持的付款方式。
5. 付款成功后刷新网页。
6. 在 ChatGPT 中确认能正常对话。

验收：

- ChatGPT 网页能打开；
- 能发出一条普通消息并收到回答；
- 账号页面显示订阅状态；
- 不要把付款截图、手机号、验证码发给 AI。

---

## 3. 安装和使用 Codex CLI

Codex CLI 是 OpenAI 的本地代码助手，可以在终端读取、修改、运行当前目录下的代码。

### 3.1 macOS / Linux 安装

```bash
curl -fsSL https://chatgpt.com/codex/install.sh | sh
```

安装后重开终端，检查：

```bash
codex --version
```

### 3.2 Windows 安装

优先二选一：

- 新手/原生 Windows：PowerShell 中按 OpenAI Windows 指南安装；
- 开发者/需要 Linux 工具：先装 WSL2 Ubuntu，再在 WSL2 里按 Linux 方法安装。

Windows 用户不要默认用管理员权限运行 Codex，除非非常清楚自己在做系统级维护。

### 3.3 登录 Codex

在终端运行：

```bash
codex
```

首次运行会要求登录：

- 选择 ChatGPT account；
- 浏览器打开登录页；
- 用刚才开通套餐的 ChatGPT 账号登录；
- 按页面提示授权；
- 回到终端。

验收：

```bash
mkdir -p ~/codex-smoke-test
cd ~/codex-smoke-test
codex
```

在 Codex 里输入：

```text
请创建一个 hello.py，运行它，并告诉我输出是什么。不要访问我的其他目录。
```

成功标准：

- Codex 能创建 `hello.py`；
- 能运行 Python；
- 能说清楚输出；
- 任何修改文件/运行命令前如有审批提示，用户能看懂并批准/拒绝。

### 3.4 Codex 使用原则

- 只在项目目录中运行 Codex，不要在用户主目录 `/` 或 `C:\` 根目录乱跑；
- 开始时要求它“先读 README / 先给计划 / 修改前说明”；
- 对删除、批量替换、安装全局依赖、访问密钥文件等请求保持警惕；
- 重要项目先用 Git：

```bash
git status
git diff
```

---

## 4. 安装 Hermes Agent

Hermes Agent 是本地 Agent 框架，支持终端、文件、Web、Skills、记忆、定时任务、消息平台 Gateway 等能力。

官方文档：

```text
https://hermes-agent.nousresearch.com/docs
```

### 4.1 安装

macOS / Linux / WSL2：

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

Windows 原生 PowerShell：

```powershell
iex (irm https://hermes-agent.nousresearch.com/install.ps1)
```

安装后重开终端，检查：

```bash
hermes --version
hermes doctor
```

### 4.2 配置模型 Provider

最简单：

```bash
hermes setup
```

或只配置模型：

```bash
hermes model
```

常见选择：

1. **OpenAI Codex**：走 ChatGPT OAuth/device code，适合已经开通 ChatGPT/Codex 的用户；
2. **Nous Portal**：一个订阅打通模型和 Tool Gateway，适合不想管理很多 API Key 的用户；
3. **OpenRouter / Gemini / Kimi / DeepSeek / Qwen / MiniMax 等**：按各自 API Key 或 OAuth 配置。

如果选 OpenAI Codex：

1. 运行 `hermes model`；
2. 选择 OpenAI Codex provider；
3. 按终端给出的设备码/浏览器链接登录；
4. 使用同一个 ChatGPT 账号授权；
5. 选择可用模型；
6. 保存配置。

### 4.3 验证 Hermes CLI

```bash
hermes chat -q "用一句中文回答：你现在能工作吗？"
```

成功标准：终端输出中文回答。

再测试工具能力：

```bash
mkdir -p ~/hermes-smoke-test
cd ~/hermes-smoke-test
hermes chat -q "请创建一个 hello.txt，内容是 hello hermes，然后读出来确认。"
```

成功标准：

- Hermes 能写文件；
- 能读回确认；
- 用户知道文件在哪个目录。

### 4.4 配置常用工具

```bash
hermes tools
```

普通用户建议先启用：

- terminal
- file
- web
- vision（如需要看图）
- skills
- memory
- session_search

启用后新开会话：

```text
/new
```

或退出重进 Hermes。

### 4.5 可选：Gateway / 飞书 / Telegram 等

先确认 CLI 正常，再配置 Gateway：

```bash
hermes gateway setup
hermes gateway status
```

不要在 CLI 还不能正常回答时就配置 Gateway，否则排错会变复杂。

---

## 5. 把流程做成 Skill 并上传 GitHub

### 5.1 创建仓库结构

```bash
mkdir -p sergio-skills/skills/mainland-gpt-codex-hermes-onboarding
cd sergio-skills
```

结构：

```text
skills/mainland-gpt-codex-hermes-onboarding/
  SKILL.md
README.md
.claude-plugin/marketplace.json
```

### 5.2 `SKILL.md` 必须包含

- 什么时候触发；
- 用户准备清单；
- 网络/VPN 合规边界；
- ChatGPT 注册、SMS、付款；
- Codex CLI 安装和验收；
- Hermes 安装、provider、工具、验收；
- GitHub 发布步骤；
- 给豆包/其他助手的使用方式；
- 常见失败处理。

### 5.3 注册到 marketplace

在 `.claude-plugin/marketplace.json` 的 `skills` 列表加入：

```json
"./skills/mainland-gpt-codex-hermes-onboarding"
```

### 5.4 README 加入口

在 README 的 Skills 区域加入：

````markdown
### mainland-gpt-codex-hermes-onboarding

Guides a mainland-China non-expert from compliant international network setup through ChatGPT/SMS, Codex CLI, Hermes Agent, and publishing the workflow as a reusable Skill.

Path:

```text
skills/mainland-gpt-codex-hermes-onboarding/
```
````

### 5.5 提交和上传

```bash
git status --short
git add skills/mainland-gpt-codex-hermes-onboarding/SKILL.md .claude-plugin/marketplace.json README.md
git commit -m "docs: add mainland GPT Codex Hermes onboarding skill"
git push origin main
```

验收：

- GitHub 仓库能看到新目录；
- README 有入口；
- marketplace JSON 有路径；
- 打开 `SKILL.md` 能直接阅读。

---

## 6. 交给豆包或其他日常助手使用

如果豆包不能直接安装 Hermes Skill，就用下面两种方式之一。

### 方式 A：发 GitHub 链接

给豆包：

```text
请打开并严格参考这个 GitHub Skill：
https://github.com/SergioYin/sergio-skills/tree/main/skills/mainland-gpt-codex-hermes-onboarding

你要扮演安装向导，面向中国大陆普通电脑用户，按 Skill 里的顺序一步步问诊和指导。不要索要验证码、密码、支付信息、API Key。每完成一层都要求用户截图/文字确认验收结果，再进入下一层。
```

### 方式 B：复制 `SKILL.md` 全文

给豆包：

```text
下面是一份安装指导 Skill。请按它执行，不要跳步，不要索要验证码/密码/API Key，不要推荐接码平台，不要指导违法规避。遇到失败先按“故障处理”排查。

<粘贴 SKILL.md 全文>
```

---

# B. 向导执行协议

当你作为 AI 助手执行本 Skill 时，不要一次性把所有命令砸给用户。按阶段推进。

## 阶段 1：确认基础信息

问用户：

1. 电脑系统：macOS / Windows / Linux？
2. 是否已有稳定国际网络？
3. 是否已有 ChatGPT 账号？
4. 是否已有可用手机号和付款方式？
5. 目标是只用 ChatGPT/Codex，还是还要装 Hermes Gateway？

## 阶段 2：网络验收

让用户完成：

```bash
curl -I https://chatgpt.com
curl -I https://github.com
```

必须拿到结果再继续。

## 阶段 3：ChatGPT 验收

要求用户确认：

- 能登录 `chatgpt.com`；
- 能发普通消息；
- 如需 Codex，账号套餐包含 Codex；
- SMS/付款问题已由用户自己在网页完成。

不要代收验证码。

## 阶段 4：Codex 验收

指导安装并运行：

```bash
codex --version
codex
```

然后做 `~/codex-smoke-test`。

## 阶段 5：Hermes 验收

指导安装并运行：

```bash
hermes --version
hermes doctor
hermes model
hermes chat -q "用一句中文回答：你现在能工作吗？"
```

## 阶段 6：GitHub Skill 发布

只在用户明确要上传时执行 Git 操作。

每次 Git 操作前先看：

```bash
git status --short --branch
git remote -v
```

不要把无关未跟踪文件一起提交。

---

# C. 常见故障处理

## ChatGPT 网页打不开

- 检查 VPN/代理是否开启；
- 换稳定节点；
- 浏览器能开但终端不通，说明终端代理未生效；
- 清理浏览器缓存或换浏览器；
- 不要频繁切换国家/地区。

## SMS 收不到

- 确认号码所属地区是否受支持；
- 确认没有拦截国际短信；
- 等几分钟，不要狂点重发；
- 使用本人长期控制的受支持真实号码；
- 不用接码平台。

## 付款失败

- 检查卡是否支持国际在线订阅；
- 账单地区、网络地区、账号地区尽量一致；
- 尝试 Apple Pay/Google Pay 等官方支持方式；
- 不要找陌生人代付绑定账号。

## Codex 登录后仍不可用

- 确认 ChatGPT 套餐包含 Codex；
- 退出重登 Codex；
- 更新 Codex：

```bash
curl -fsSL https://chatgpt.com/codex/install.sh | sh
```

- 如果账号 entitlement 同步异常，只能等官方恢复或联系 OpenAI 支持。

## Hermes 找不到命令

- 重开终端；
- macOS/Linux 执行：

```bash
source ~/.zshrc || source ~/.bashrc
which hermes
```

- 仍失败则重新安装。

## Hermes 模型不可用

- 重新运行：

```bash
hermes model
```

- 换一个 provider；
- 检查 API Key/OAuth 是否有效；
- 先用 `hermes chat -q "hi"` 验证，不要先上 Gateway。

---

# D. 完成标准

本 Skill 指导成功的最低标准：

- 用户能稳定访问 ChatGPT/GitHub；
- 用户能登录 ChatGPT 并正常对话；
- 用户能在终端运行 Codex CLI 并完成一个小文件任务；
- 用户能运行 Hermes CLI 并完成一次中文回答；
- 如用户要求发布，GitHub 仓库中存在 Skill 目录、README 入口和 marketplace 注册；
- 整个过程中没有泄露验证码、密码、支付信息、API Key。
