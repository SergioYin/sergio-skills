---
name: mainland-gpt-codex-hermes-onboarding
description: Guide a mainland-China non-expert from compliant VPN/international network setup through ChatGPT account/SMS, Codex 桌面版/App（CLI 备用）、Hermes Agent, and publishing the workflow as a GitHub Skill that another daily assistant such as 豆包 can follow.
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
3. **手机号现实情况**：OpenAI 帮助页当前说明 ChatGPT 新账号/普通 ChatGPT 使用通常不再要求手机验证；但 API 首个 Key、异常风控、特定地区/账号状态仍可能触发 SMS/WhatsApp 验证。若出现验证，使用本人长期控制的真实号码；不要用一次性接码平台。
4. **分层验收**：网络能访问 → ChatGPT 能登录 → Codex App 能工作 → Hermes CLI 能工作 → 再配置 Gateway/Skills/GitHub。

## 一页总流程

```text
准备电脑和浏览器
→ 配置合规稳定的国际网络环境（VPN/代理/公司网络/境外网络，按用户合法可用方式）
→ 注册/登录 ChatGPT
→ 通过 SMS/邮箱/支付验证并开通可用套餐
→ 安装并登录 Codex 桌面版/App（CLI 备用）
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

## 2. 注册或登录 ChatGPT：详细到页面动作

> 当前官方帮助页要点：ChatGPT 新账号/普通 ChatGPT 使用通常**不再要求手机验证**；但 API 平台创建首个 API Key 仍可能要求手机验证。若出现手机验证，验证码只能通过 SMS，或在部分国家/地区通过 WhatsApp；不能改成邮箱或电话语音。实际页面以 OpenAI 当时风控为准。

### 2.1 注册前先做“干净环境”

普通用户先做这几件事，减少风控和页面异常：

1. 打开稳定国际网络，注册期间不要频繁切换国家/地区。
2. 使用常用浏览器的无痕窗口，或清理旧的 `chatgpt.com` / `openai.com` Cookie。
3. 电脑系统时间、时区自动同步，浏览器不要装太多奇怪插件。
4. 准备一个长期邮箱：Gmail / Outlook / iCloud / Proton / 公司邮箱均可；不建议用临时邮箱。
5. 如果要付费，准备官方页面可接受的付款方式；不要找陌生人代付或代绑账号。

验收：浏览器能打开：

```text
https://chatgpt.com
https://help.openai.com
https://developers.openai.com/codex/app
```

### 2.2 进入注册页

1. 打开：

```text
https://chatgpt.com
```

2. 点 **Sign up**。如果已有账号，点 **Log in**。
3. 推荐优先使用：
   - Google 登录；
   - Apple 登录；
   - Microsoft 登录；
   - 或邮箱 + 密码。

经验规则：

- 如果用户本来就有 Gmail / Apple / Microsoft 账号，用第三方登录更少记密码；
- 如果用邮箱密码注册，密码要保存到密码管理器；
- 以后 Codex App、Codex CLI、Hermes OpenAI Codex provider 尽量都使用这个同一个 ChatGPT 账号。

### 2.3 邮箱验证

如果使用邮箱注册：

1. 输入邮箱。
2. 设置密码。
3. 打开邮箱收信。
4. 找到 OpenAI / ChatGPT 验证邮件。
5. 点击 **Verify email address** 或类似按钮。
6. 回到 ChatGPT 页面继续。

如果收不到邮件：

- 查垃圾邮件 / 促销 / 通知分类；
- 等 1–3 分钟再点重发；
- 不要连续高频重发；
- 换一个长期可用邮箱。

### 2.4 填姓名 / 生日 / 基础资料

页面可能要求：

- 姓名；
- 出生日期；
- 用途或个性化问题。

按真实信息填写。不要为了“看起来像外国人”乱填身份信息；未来账号恢复、付款、风控可能会用到这些一致性。

### 2.5 SMS / WhatsApp 手机验证

如果页面要求手机验证：

1. 选择手机号所属国家/地区。
2. 输入本人长期控制的真实手机号。
3. 选择页面给出的接收方式：
   - SMS；
   - 或 WhatsApp（仅当该国家/地区页面显示支持）。
4. 收到一次性验证码后，由用户自己填入网页。

重要规则：

- AI 助手不要索要、代填、保存验证码；
- 不要把验证码发给任何人；
- 官方帮助页说明：验证码不能改成邮箱或电话语音；只能 SMS，或部分地区 WhatsApp；
- OpenAI 帮助页也说明：ChatGPT 新账号/普通 ChatGPT 使用通常不再要求手机验证，但 API 首个 Key 可能要求；所以如果用户在某一步遇到 SMS，要先判断是在 ChatGPT 页面还是 platform/API 页面。

如果 `+86` 或当前号码不可用：

- 不要反复高频尝试，容易触发风控；
- 不要使用一次性接码平台、共享号码、临时号；
- 可以使用本人长期控制、所在地区受支持的真实号码/eSIM/长期境外号码；
- 如果没有合适手机号，先完成 ChatGPT 网页可用性；Codex/Hermes 可以暂时走其他 provider（Nous Portal、OpenRouter、Gemini、Kimi、DeepSeek、Qwen、MiniMax 等），不要把整套安装卡死。

> 网上很多中文教程会推荐“海外接码平台 / 虚拟卡 / 代升级”。这类方案容易违反平台条款、导致找回困难或封号；本 Skill 只保留风险提醒，不给可执行接码步骤。

### 2.6 首次登录后验收 ChatGPT

进入 ChatGPT 主界面后，做最小测试：

```text
请用一句中文回答：你现在可以正常工作吗？
```

成功标准：

- 能进入 ChatGPT；
- 能发出消息；
- 能收到回答；
- 左下角/账户菜单能打开 Settings / Plan / Subscription。

### 2.7 开通 Plus / Pro / 可用套餐

Codex App / CLI 官方文档说明：Codex 包含在 ChatGPT Plus、Pro、Business、Edu、Enterprise 等计划中；实际权益以账号页面和 OpenAI 当前价格页为准。

操作：

1. 在 ChatGPT 左下角点头像/账号菜单。
2. 找到 **Upgrade plan** / **Plan** / **Subscription**。
3. 选择 Plus、Pro 或团队计划。
4. 进入官方结账页。
5. 使用官方支持的付款方式。
6. 付款成功后刷新 ChatGPT。
7. 再打开账号菜单确认订阅状态。

付款失败排查：

- 卡是否支持国际在线订阅；
- 卡是否开启境外/线上支付；
- 网络地区、账单地区、付款方式地区尽量一致；
- Apple Pay / Google Pay 如果页面支持，可优先试；
- 不要把付款卡号、CVV、短信码发给助手；
- 不要找陌生人代付绑定账号。

完成标准：

- ChatGPT 网页正常对话；
- 账号页面能看到当前 plan；
- 能访问 Codex App 下载页面：

```text
https://developers.openai.com/codex/app
```

---

## 3. 安装和使用 Codex 桌面版（优先）

Codex App 是 OpenAI 的桌面端“Codex 指挥中心”，适合普通人使用。它支持 macOS 和 Windows，可管理多个项目、多个线程、Git worktree、自动化、内置终端、Git diff/commit/PR 等。CLI 作为备用或高级路线。

### 3.1 下载 Codex App

官方入口：

```text
https://developers.openai.com/codex/app
```

macOS：

- Apple Silicon Mac：下载 Apple Silicon 版 `Codex.dmg`；
- Intel Mac：下载 Intel/x64 版 `Codex-latest-x64.dmg`；
- 不确定芯片：点左上角 Apple 菜单 → About This Mac，看 Chip / Processor。

Windows：

- 官方页面会跳到 Microsoft Store / 安装器；
- 也可在 PowerShell 中安装：

```powershell
winget install Codex -s msstore
```

不要从不明网盘、破解版网站下载 Codex。

### 3.2 安装并登录

macOS：

1. 打开 `.dmg`。
2. 把 Codex 拖入 Applications。
3. 从 Applications 打开 Codex。
4. 如果系统拦截，确认来源是 OpenAI 官方下载，再在系统设置里允许打开。

Windows：

1. 从 Microsoft Store / 官方安装器安装。
2. 打开 Codex。
3. 首次启动时按提示登录。

登录方式：

- 优先选择 **ChatGPT account**，使用前面开通的同一个账号；
- 也可以用 OpenAI API key，但官方说明部分功能可能不可用；普通用户不优先推荐。

### 3.3 第一次添加项目

1. 在桌面新建一个安全测试目录：

macOS / Linux / WSL2：

```bash
mkdir -p ~/codex-smoke-test
```

Windows PowerShell：

```powershell
mkdir $HOME\codex-smoke-test
```

2. 打开 Codex App。
3. 点击 **Add project** / **Open project**。
4. 选择刚才的 `codex-smoke-test` 文件夹。
5. 确认模式选择 **Local**，不要一开始就选 Full Access。
6. 发第一条消息：

```text
请在当前项目里创建一个 hello.py，运行它，并告诉我输出是什么。不要访问当前项目以外的目录。
```

成功标准：

- Codex App 能在项目中创建文件；
- 能运行命令或展示需要用户批准的命令；
- 用户能在 App 里看到修改、终端输出、diff 或总结；
- 没有访问项目外目录。

### 3.4 Windows Codex App 特别设置

Windows Codex App 支持两种 agent：

1. **Windows native**：默认，命令在 PowerShell 里跑，使用 Windows 原生 sandbox；
2. **WSL2**：agent 在 WSL2 里跑，使用 Linux sandbox。

普通 Windows 用户建议：

- 没有 Linux 开发需求：先用 Windows native；
- 项目依赖 Linux 工具链：安装 WSL2，再在 Codex Settings 里把 agent 切到 WSL，并重启 App。

如果使用 Windows native：

- 项目优先放在 Windows 文件系统，例如 `C:\Users\你的用户名\Projects\xxx`；
- 不要默认用管理员身份打开 Codex；
- sandbox 权限保持 Default permissions；
- Full Access 风险高，只有在明确需要且已备份项目时再考虑。

常用开发工具可用 winget 安装：

```powershell
winget install --id Git.Git
winget install --id OpenJS.NodeJS.LTS
winget install --id Python.Python.3.14
winget install --id GitHub.cli
```

### 3.5 Codex App 使用原则

- 一个项目一个 Project，不要把整个用户主目录加进去；
- 新任务优先用 **Worktree** 隔离，尤其是同一个 repo 内并行多个任务；
- 让 Codex 先读 README / AGENTS.md / package.json / 测试命令；
- 让 Codex 先给计划，再改文件；
- 在 Diff 面板里看修改，再决定 stage / revert / commit；
- 对删除文件、批量替换、安装全局依赖、访问密钥文件、Full Access 等请求保持警惕；
- 重要项目先检查：

```bash
git status
git diff
```

### 3.6 CLI 备用路线

如果 Codex App 安装失败，或用户更适合终端：

macOS / Linux：

```bash
curl -fsSL https://chatgpt.com/codex/install.sh | sh
codex --version
codex
```

Windows：

- 优先用 Codex App；
- 需要 CLI 时可用官方 Windows 指南或 WSL2 路线。

---

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
- Codex 桌面版/App 安装和验收，CLI 作为备用；
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

Guides a mainland-China non-expert from compliant international network setup through ChatGPT/SMS, Codex 桌面版/App（CLI 备用）、Hermes Agent, and publishing the workflow as a reusable Skill.

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

## 阶段 4：Codex App 验收

指导用户：

1. 从 `https://developers.openai.com/codex/app` 下载官方 Codex App；
2. 用同一个 ChatGPT 账号登录；
3. 新建 `~/codex-smoke-test` 或 `%USERPROFILE%\codex-smoke-test`；
4. 在 Codex App 里 Add/Open project；
5. 选择 Local + 默认 sandbox 权限；
6. 让 Codex 创建并运行 `hello.py`，确认能看到文件修改和输出。

CLI 只作为备用路线，不作为普通用户主路径。

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

## Codex App 登录后仍不可用

- 确认 ChatGPT 套餐包含 Codex，且使用的是同一个 ChatGPT 账号；
- 退出 Codex App 后重登；
- Windows 版优先从 Microsoft Store / 官方链接更新；
- macOS 版优先从 `https://developers.openai.com/codex/app` 重新下载官方安装包；
- 如果只是不想用 App，可临时走 CLI 备用路线：

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
- 用户能在 Codex App 中添加本地测试项目并完成一个小文件任务；
- 用户能运行 Hermes CLI 并完成一次中文回答；
- 如用户要求发布，GitHub 仓库中存在 Skill 目录、README 入口和 marketplace 注册；
- 整个过程中没有泄露验证码、密码、支付信息、API Key。
