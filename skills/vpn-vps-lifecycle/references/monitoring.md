# 监控与持续验证

健康监控、代理业务监控和卖家声明审计是三层不同证据。基础 ping 成功不能替代真实网站与客户端路径验收。

## 五分钟轻量采样

- CPU/load/steal、内存、Swap、OOM、磁盘/inode。
- 网卡字节、errors/drops、TCP 连接、NTP、boot ID、失败单元、防火墙状态。
- 已选协议的 unit/interface 状态、重启计数、监听、最近错误和本地统计；WireGuard 还记录 peer 最近握手与传输字节，管理 API 只能监听 loopback。
- 按设备/协议的流量、小时/日/月聚合、配额阈值。
- 用户指定网站的 DNS、connect、TLS、TTFB、total、HTTP 状态和 remote IP。
- 数据库/报告新鲜度和保留任务状态。

连续失败达到用户约定次数后再告警，避免单次 DNS、路由或 HTTP 抖动制造噪声。

## 客户端路径采样

服务器直接访问只证明 VPS 出站。至少从一个真实客户端分别经每个已选协议测试关键站点，并记录：

- 选择器和协议，不静默改变用户当前节点。
- DNS、连接、TLS、TTFB、总耗时、返回码、出口 IP。
- Wi-Fi/蜂窝、家庭 ISP、时间窗口和客户端休眠状态。

## 可执行 burn-in 证据链（REALITY 纵向切片）

先取得用户对测试流量预算的当前明确授权，用 `update_state.py authorize --kind test-traffic` 记录非秘密证据引用，再填写 `private/burn-in-plan.json`：记录用户批准时间、客户端所在地 IANA 时区、晚高峰起止、至少三个**不同日期**、客户端/服务器最大对齐分钟数、下载 payload 字节预算、CPU steal、可用内存和磁盘阈值。`test_byte_budget` 只统计 curl 下载 payload，是实际网络总流量的下界；还要为 TLS、代理和其他业务测试预留余量。

每个晚高峰窗口按同一顺序采集：

1. 在真实客户端运行 `client_acceptance.py`，其 JSON 必须包含出口匹配、逐 URL 延迟、HTTP 状态和 `curl_size_download_bytes`。
2. 在允许的对齐时间内，从 VPS 只读采集服务、监听、NTP、失败单元、boot ID、重启计数、CPU steal、内存、磁盘、网卡累计字节和路由指纹。可避免在服务器落盘：

```bash
ssh -p <SSH_PORT> <ADMIN_USER>@<VPS_IP> \
  'python3 - --port 443 --output -' \
  < scripts/collect_server_health.py \
  > <task-dir>/private/server-health-window.json
chmod 600 <task-dir>/private/server-health-window.json
```

3. 填写权限 0600 的 `private/burn-in-context.json`，用非识别性设备 ID 和匿名地区/运营商说明本次真实设备、网络、协议及 rule/global/SSH-loop/业务检查。
4. 把三份证据封存为只读窗口文件：

```bash
python3 scripts/record_burn_in.py \
  --plan <task-dir>/private/burn-in-plan.json \
  --acceptance <task-dir>/evidence/client-acceptance-window.json \
  --health <task-dir>/private/server-health-window.json \
  --context <task-dir>/private/burn-in-context.json \
  --windows-dir <task-dir>/evidence/burn-in/windows \
  --label <non-identifying-window-label>
```

记录器拒绝非晚高峰、时间未对齐、客户端/服务器失败、人工检查失败和覆盖已有窗口；输出权限为 0400，并用内嵌 SHA-256 封存。0400 与 hash 用于降低误改和发现不一致，不是对拥有本机完整权限者的密码学防篡改保证。

达到计划日期数后，禁止手写 PASS，必须计算 summary：

```bash
python3 scripts/summarize_burn_in.py \
  --plan <task-dir>/private/burn-in-plan.json \
  --windows-dir <task-dir>/evidence/burn-in/windows \
  --output <task-dir>/evidence/burn-in/summary.json
```

聚合器重验 seal、计划 hash、日期/时段、样本、出口一致性、流量预算、P50/P95/P99、boot/路由/重启漂移和资源阈值。状态机还会现场重算并逐字段比较，人工写一个 `result: PASS` 不能进入 `accepted`。

## 卖家声明漂移

- 每日或低频：实际分配 IP 的 BGP origin、注册/位置变化和少量 AS-path fingerprint。
- 每周或按需：固定字节上下行样本和匿名业务可达性。
- 月度重置点：guest 网卡计数与供应商面板对账。
- 路由、IP、hypervisor、内核、套餐变化后：重新执行完整点验。

每次吞吐测试都声明字节/时间预算。高频测速会扭曲月流量与性能结论。

## 保留与权限

- 结构化明细保留期与汇总保留期分别定义；磁盘较小时优先保留聚合而非无限日志。
- 包含设备 ID、IP 或业务目标的原始样本视为敏感；限制权限并在分享前聚合/脱敏。
- 报告可公开服务状态和统计范围，不公开 Secret、完整客户端 ID、真实管理地址或个人站点清单。
