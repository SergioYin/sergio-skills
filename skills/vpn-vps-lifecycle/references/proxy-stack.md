# 协议选择与部署

只安装用户明确选择的协议。部署前从官方文档和发布页核对当前稳定版本、架构、校验值、配置语法和兼容性；不要固定沿用本 skill 制作时的版本。

官方入口：

- Hysteria 2：<https://v2.hysteria.network/docs/>
- Hysteria 2 performance：<https://v2.hysteria.network/docs/advanced/Performance/>
- Project X / Xray：<https://xtls.github.io/>
- REALITY：<https://xtls.github.io/en/config/transports/reality.html>
- WireGuard protocol：<https://www.wireguard.com/protocol/>
- WireGuard quick start：<https://www.wireguard.com/quickstart/>

## 共同安全要求

- 从官方 release 获取二进制并校验 checksum/signature；拒绝不透明的一键脚本。
- HY2/Xray 使用独立、无登录 shell 的服务账户；WireGuard 私钥和配置也必须 root-only，但不要为内核接口生搬硬套用户态服务账户要求。
- 每台设备使用独立凭据，方便审计和单独轮换；不在聊天、报告或版本库中打印完整值。
- 使用 hardened systemd unit：限制写目录、能力和系统调用，同时确保协议所需网络权限。
- 统计/管理 API 仅监听 loopback，Secret 单独保存；防火墙不暴露它。
- 选择 HY2 与常见 REALITY/RAW/TCP 组合时，TCP 443 与 UDP 443 可由不同服务同时使用，但必须分别验证监听和外部路径。

## HY2

HY2 基于 QUIC/UDP。部署时确认：

- 供应商允许目标 UDP 端口，客户端运营商路径未阻断或严重整形 UDP/QUIC。
- 使用可信证书和正确 SNI；生产配置默认不依赖 `skip-cert-verify`。
- 带宽/拥塞控制参数来自真实测量，不把端口宣传值直接当可用持续速率。
- userspace QUIC 可能消耗更多 CPU；监控 CPU、steal、内存、包丢失和延迟抖动。
- 若启用流量统计，验证每个设备 ID 的流量和 online 语义；online 实例数不等于浏览器请求数。

## VLESS/REALITY

REALITY 是传输安全层，应核对它与当前 Xray transport 的兼容性。对于常见 VLESS + REALITY + Vision + RAW/TCP 部署：

- 为每台设备生成独立 UUID/short ID；服务器私钥只留在 root-only 配置，客户端只获得公钥材料。
- 选择合适的 target/server name，并用当前 Xray 工具验证目标握手行为；不要把会导致开放转发或异常特征的目标当默认值。
- 配置测试通过后再启动服务，检查 unit、重启计数、journal、TCP 监听和外部客户端握手。
- 如果选择 XHTTP 或 gRPC，必须按该组合重新验证；不能把 RAW/TCP 的结论直接复用。
- Mihomo 客户端与 Xray 服务端存在版本兼容性风险；当前 Mihomo 文档明确提示 Xray v26.7.11+ 的不兼容变更。每次部署必须固定并记录两端版本、读取当前文档并做真实握手，不得机械安装最新 Xray。选择 Ubuntu + REALITY + Mihomo 时使用 [deployment-reality-mihomo.md](deployment-reality-mihomo.md) 的兼容性门禁和可执行纵向切片。

## WireGuard

WireGuard 是标准三层 VPN；协议外层全部使用 UDP。它适合远程访问私网、站点互联或在 UDP 可用的受控网络中建立简洁隧道，不以伪装成 HTTPS/REALITY 流量为目标。部署时确认：

- 供应商与客户端网络允许所选 UDP 端口；若 UDP 被阻断，不能把更换 WireGuard 参数当作 TCP 备用。
- 每个 peer 使用独立密钥；私钥权限最小化，撤销某台设备时不影响其他 peer。
- `AllowedIPs` 按用途最小化：远程私网只路由私网前缀；全隧道才使用默认路由，并同时设计 IPv4、IPv6、DNS 和 kill-switch 行为。
- 需要 VPS 做互联网出口时，明确启用 IP forwarding、NAT 和最小防火墙；不要把管理地址或内网管理路径错误送回隧道。
- `PersistentKeepalive` 只在 NAT 后 peer 需要保持入站可达时设置，并按官方建议从保守值开始，不把它当作普通性能开关。
- 使用 `wg show` 验证最近握手、传输字节和 peer 状态，再从真实设备验证目标私网、出口 IP、DNS、休眠恢复和网络切换。

## 变更顺序

1. 备份现有服务、配置和防火墙状态。
2. 安装到版本化路径，准备配置和 systemd unit。
3. 运行官方语法/配置测试。
4. 启动并检查本机监听、journal 与重启计数。
5. 只开放所选协议需要的 TCP/UDP 端口；WireGuard 出口模式还要核对 forwarding 与 NAT。
6. 从外部物理客户端验证握手和出口 IP。
7. 重启验收需另行授权；完成后重复端到端测试。

任何一步失败都应停止扩大变更，保留原管理通道并使用已记录的回滚路径。
