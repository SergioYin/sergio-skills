---
name: market-quick-take
description: Fast single-message verdict protocol for "X 涨/跌了为什么？能不能买？现在什么位置？" style questions on stocks, ETFs, crypto, FX, rates, or sports-market odds. Use for quick takes that need a conclusion within one reply; hand off to equity-research-briefing when the user asks for a full sourced briefing, broker views, or multi-company comparison.
version: 1.0.0
author: SergioYin
license: MIT
metadata:
  hermes:
    tags: [markets, quick-take, trading, freshness-check, decision-support]
    related_skills: [equity-research-briefing, investment-discipline-coach, scheduled-web-monitoring]
---

# Market Quick Take（行情快评协议）

## Class of Task

在**一条回复内**给出可操作的行情判断：结论 → 概率 → 操作优先级 → 纪律。不是研报，不是科普。

## When to Use

- 「X 为什么涨/跌？」「能不能买？」「现在加仓还是等？」
- 「今天 X 走势怎么看？」「财报前怎么办？」
- 盘口/赔率快评（体育博彩同样适用此协议）。

**转交**：用户要「大行怎么看/目标价/催化剂全景/多公司对比」→ `equity-research-briefing`；用户在亏损后情绪化倾诉 → `investment-discipline-coach`（先接情绪，后谈纪律）。

## Step 0 — 数据新鲜度守门（不可跳过）

历史事故：韩股休市日把上个交易日收盘价当实时价；世界杯赛程用了过期缓存。

回答任何时效性问题前：

1. 确认今天日期与目标市场时区的**当前时间**。
2. 确认目标市场**今天是否开市**（节假日/休市日历），盘前/盘中/盘后。
3. 拿到报价后核对**数据时间戳**；对不上就明说「这是 X 时刻的数据」。
4. 韩股、港股、A股的休市日历互不相同，不要用美股直觉套。

## 回复形状（固定四段，默认 <200 字正文）

```text
结论：<一句话：买/不买/等/减，或涨跌主因>
概率：<关键情景的粗概率或置信度，如"继续上行 60%，回踩 xx 概率 30%">
操作：<按优先级排列的 1-3 个动作，含仓位/价位/条件>
纪律：<一条，只提最相关的那条，不说教>
```

规则：

- 结论永远第一句。禁止先铺背景。
- 概率给粗估并标注依据（盘口隐含、期权 IV、历史 base rate），不假装精确。
- 操作必须可执行：有价位、有条件、有仓位上限。
- 纪律一条封顶。用户已明确讨厌泛泛说教。
- 不下单、不碰账户；输出仅供参考的边界在系统层，不必每次口头声明。

## 证据规则

- 价格、财报日期、事件时间一律现查，不背记忆。
- 传闻类（「有人花 600 万买 Call」）：先核实来源再评论，标注 已证实/未证实。
- 抖音/小红书财经视频的说法：默认存疑，找一手数据（filing、交易所、期权链）对照。

## Done 检查

- [ ] 走过 Step 0（有市场开闭与时间戳确认）
- [ ] 四段形状齐全且结论在第一句
- [ ] 至少一个数字有来源
- [ ] 正文没超过一屏（飞书视角）
