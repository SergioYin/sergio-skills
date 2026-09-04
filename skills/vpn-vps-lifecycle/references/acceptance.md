# 验收与 burn-in

使用 [../assets/claim-matrix.md](../assets/claim-matrix.md) 和 [../assets/acceptance-report.md](../assets/acceptance-report.md) 输出证据。不要用一个总的“通过”掩盖不同声明的证据质量。

## 即时验收

### 规格与控制面

- vCPU、guest 内存、虚拟磁盘、OS、内核、虚拟化、面板套餐、账期和流量重置日。
- 明确 DDR、物理 SSD、宿主机超售和物理 uplink 等 guest 无法证明的边界。
- VNC/console、reinstall/rescue 和凭据恢复能够使用。

### 网络与卖家声明

- 对实际分配 IP 与每个公开测试 IP 分别查询 BGP origin、RIR、RPKI、WHOIS、位置和信誉。
- 路由声明必须区分去程/回程、运营商、地区、目标和时间；记录完整 AS-path，而不是只截取期望 AS 号。
- 中间路由器 ICMP loss 在后续 hop/终点正常时不等于端到端丢包。
- 使用固定字节预算做上/下行多样本，记录 endpoint、协议、样本范围和开销。
- 匿名 HTTP 成功只证明初步可达；流媒体、AI、支付等完整解锁需要真实登录、目录/播放/API 业务验收。

### 系统与服务

- key-only 管理登录和 sudo，`sshd` 有效配置，最小防火墙，Fail2ban，NTP，无异常失败单元。
- 已选协议的配置语法、unit/interface 状态、重启计数、日志和预期监听；HY2/REALITY 分别验证 UDP/TCP 外部路径，WireGuard 验证最近握手、peer 字节、forwarding/NAT 与路由。
- 授权重启后重复登录、服务、监听、防火墙和客户端测试。

### 客户端

- 每台物理设备/协议返回预期 VPS 出口 IP。
- 桌面管理 SSH route 使用物理网关而非 TUN/utun，避免自循环。
- 选择 Clash Meta/Mihomo 时，全局模式的明确叶子节点可用，规则模式显示预期组并真正遵守规则；选择 WireGuard 时，分别验证分流/全隧道、DNS 和断线策略。
- Android 完成后台、锁屏、网络切换、应用重启和授权后的设备重启测试。

## 多日 burn-in

按风险与退款窗口确定周期，至少覆盖：

- 多个晚高峰、工作日/周末和重要客户端运营商。
- 成功率、P50/P95/P99、丢包、抖动、吞吐、CPU/steal、内存、磁盘和服务重启。
- 实际网站、登录/播放/API、目标设备并发。
- 路由/ASN/位置漂移、供应商面板流量对账和月度用量外推。
- 主协议失败时的协议备用；整机失败则验证第二故障域或恢复演练。

## 结论状态

每项卖家声明使用最窄的状态：

- `confirmed`：目标属性被直接、可复现地验证。
- `supported`：证据支持但存在范围或时间限制。
- `inconsistent`：观察与声明冲突。
- `control-plane-only`：只有订单/面板证据。
- `not yet proven`：尚无足够证据。

最终决策使用 `keep`、`keep with limitation`、`request remediation/refund` 或 `reject`，并列出回滚、剩余风险和下一次复核时间。
