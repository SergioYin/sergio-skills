---
name: hermes-self-update
description: Runbook for updating the local Hermes Agent from upstream. Use when the user says 更新 Hermes/拉取最新/升级到最新版/合并 upstream, or when the upstream watcher reports updates worth applying. Preserves local patch design intent, verifies the gateway end-to-end after restart, and keeps a rollback path.
version: 1.0.0
author: SergioYin
license: MIT
metadata:
  hermes:
    tags: [hermes, ops, update, runbook, rollback]
    related_skills: [hermes-macbook-ops]
---

# Hermes Self-Update Runbook

## Class of Task

把「更新 Hermes」从一次性冒险变成固定 runbook：fetch → 本地补丁意图核对 → merge → 重启 → 端到端验证 → 回滚路径。历史事故：升级后 gateway 自我重启能力静默回归；模型切换宣称完成但未生效。**结论：没有验证闭环的更新等于没更新。**

## When to Use

- 「帮我把本地 Hermes agent 更新到最新」「拉取远端最新代码，处理好冲突」
- upstream watcher 日报提示有值得合入的更新，且健哥点头。

不要在健哥未发话时主动执行更新（watcher 只读汇报，本 runbook 只在授权后跑）。

## 前置事实

- 源码：`/Users/xjyin/workspace/system/hermes-agent`；home：`~/.hermes`。
- 本地有自有补丁（如 feishu 路由、image_gen backend）。**健哥的铁律：补丁的设计意图必须活在 commit message / 记忆 / runbook 里，合并时保意图，不是保代码表面。**
- OpenClaw 服务无关且不可触碰。

## 步骤

### 1. 快照
```bash
cd /Users/xjyin/workspace/system/hermes-agent
git status --short          # 有未提交改动先提交（WIP 也提）
git rev-parse HEAD          # 记录回滚点
git log --oneline origin/main..HEAD   # 列出本地补丁清单
```
把回滚 commit 和本地补丁清单写进本次更新的 todo/报告。

### 2. 审阅 upstream
```bash
git fetch origin
git log --oneline HEAD..origin/main
```
扫一遍新提交，**重点标出触碰本地补丁同一区域的提交**（gateway、路由、provider 配置），这些是回归高危区。

### 3. 合并（保意图）
- 冲突时：先读本地补丁的 commit message 找设计意图，按意图重写，而不是机械选边。
- 意图不明的旧补丁：停下来问健哥，不猜。
- 合并后跑得起来的最小检查：`hermes --version` / 单测（若有）。

### 4. 重启 gateway
按 `hermes-macbook-ops` 的方式重启。不动 OpenClaw。

### 5. 端到端验证（全部通过才算完成）
- [ ] gateway 进程存活，且**自我重启能力**仍在（历史回归点，单独验证）。
- [ ] 默认模型/provider 与配置一致：查真实运行状态，不是查配置文件。
- [ ] 飞书往返一条测试消息（home channel），确认收发与引用回复位置正常。
- [ ] cron jobs 仍在列表且下次触发时间正确。
- [ ] 本地补丁行为抽查一项（如 feishu 话题路由）。

**SOUL.md / skill 改动的生效边界（2026-07-07 实测）**：session 的 system prompt 在会话创建时定格，改 SOUL.md 或新装 skill 对**正在进行的会话不生效**。验证前必须先发 `/new` 重置会话，否则会误判"改动无效"。skill 注册本身无需重启 gateway（snapshot 带 mtime manifest 自动失效）。

### 6. 收尾
- 报告：新版本号、合入的 upstream 变更两三句、冲突及意图处理方式、验证清单结果。
- 有价值的合并教训 → 追加进本 skill 或记忆。

## 回滚

任一验证失败且 10 分钟内修不好：
```bash
git reset --hard <步骤1记录的回滚点>
```
重启 gateway，重跑第 5 步验证，然后向健哥报告失败原因——**不要带病运行，也不要连试三种修法**（两次失败即停，给分析和选项）。

## 反模式

- ❌ 「已经切换/已经生效」但没有回读真实状态。
- ❌ 合并冲突按代码表面取舍，丢掉补丁意图。
- ❌ 验证只看进程在不在，不测行为（自我重启回归就是这么漏掉的）。
- ❌ 更新和其他改动混在一个批次，出问题无法归因。
