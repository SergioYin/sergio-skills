---
name: hermes-cron-authoring
description: Template and guardrails for writing Hermes cron job prompts. Use whenever the user asks to create, revise, or brainstorm a 定时任务/cron/每日提醒/监控任务, so boundary boilerplate (read-only, no trading, output shape, timezone, expiry) is generated from template instead of hand-typed each time.
version: 1.0.0
author: SergioYin
license: MIT
metadata:
  hermes:
    tags: [cron, automation, templates, guardrails]
    related_skills: [scheduled-web-monitoring]
---

# Hermes Cron Authoring（定时任务撰写模板）

## Class of Task

把「我想每天 X 点做 Y」一句话，展开成边界完整、输出形状固定、可退役的 cron prompt。历史上边界样板（只读/不下单/不构成投资建议）被手写了 100+ 次——这些从此由模板生成。

## When to Use

- 「做一个定时任务…」「每天 X 点提醒我…」「帮我盯着…」（若纯监控优先考虑 `scheduled-web-monitoring`）
- 修改现有 cron 的时间、范围、输出。
- 用户只有模糊想法（「每日选股该做什么，头脑风暴一下」）→ 先用本模板的字段清单反问补齐，再写 prompt。

## 必答字段（写 prompt 前先确认）

1. **触发**：cron 表达式 + 时区（默认 Asia/Singapore；涉及外盘先换算并写明两地时间）。
2. **数据窗口**：看过去多久的数据？（如「过去 24h」「上一交易日」）
3. **投递**：发到哪个飞书频道/群？文字还是语音？
4. **输出形状**：固定段落结构，默认「结论先行 + 只报有变化的」。
5. **静默条件**：什么情况下不发或只发一行「无变化」？（防日报噪音化）
6. **退役条件**：有限期任务（如赛事、财报季）必须写自动停止判据。

## Prompt 模板

```text
你是健哥的 MacBook 管家。<一句话任务定位>。

边界：
- 只读任务：不下单、不发外部消息、不修改任何账户/配置/文件。
- 不构成投资建议（涉及行情时保留此条，否则删）。
- 数据现查，不用记忆；给出数据时间戳；来源存疑要标注。
- 若目标市场今日休市/赛事已结束/来源不可达：只发一行说明，不硬凑内容。

任务：
- <数据窗口 + 覆盖对象>
- <判断规则：什么算"有变化/触发信号">

输出（发到 <频道>，中文，结论先行，默认短）：
1. <固定段落 1>
2. <固定段落 2>
- 无实质变化时：只发一行「今日无变化」。

退役：<条件，如"决赛结束后自行停止并通知健哥删除本任务"；长期任务写"无">
```

## 反模式

- ❌ 每天硬凑一篇长报告（没变化也写满）——静默条件是必填项。
- ❌ 有限期任务无退役条款，赛事结束后继续空转。
- ❌ 时区只写 cron 表达式不写语义时间，外盘任务错峰（13F 案例：08:30 改 11:30 才收得齐）。
- ❌ 在 prompt 里省略边界样板，指望模型自觉。

## Done 检查

- [ ] 六个必答字段全部落实
- [ ] 边界段完整
- [ ] 有静默条件与退役条件
- [ ] 首次运行后核对了实际投递效果（时间、频道、长度）
