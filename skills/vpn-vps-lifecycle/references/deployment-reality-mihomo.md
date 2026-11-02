# 可执行纵向切片：Ubuntu + VLESS/REALITY + Mihomo

这是当前包唯一提供脚本化部署的协议路径。HY2 与 WireGuard 仍使用 [proxy-stack.md](proxy-stack.md) 的指导和当前官方文档，不得假装拥有同等自动化覆盖。

该切片执行：可恢复任务目录、只读远端发现、私密配置渲染、固定版本与 checksum 校验、计划预览、Xray 原子式部署、失败自动回滚、服务端 postcheck、Mihomo 桌面/Android 配置和真实网站验收。它不会自动购买、改变 SSH、启用防火墙或重启。

## 兼容性门禁

每次部署都要记录 Xray 与 Mihomo 的精确版本并查询当前官方兼容性。Mihomo 当前文档明确警告其 REALITY 客户端不兼容 Xray v26.7.11+ 的有意变更；因此渲染器默认拒绝这一组合。可选处理：

1. 选择当前仍受信任且经双方实测兼容的 Xray 版本，并接受固定旧版本的维护风险。
2. 改用当前兼容的服务端实现，并为该实现建立新的模板与测试，不能直接复用本脚本。
3. 改选 HY2 等已验证路径。

只有取得独立端到端证据时，才可在输入中设置 `allow_unverified_mihomo_compatibility=true`；这个字段不是“忽略警告”开关。

事实入口：Xray [REALITY](https://xtls.github.io/en/config/transports/reality.html)、[命令参数](https://xtls.github.io/en/document/command.html)、[安装与校验](https://xtls.github.io/en/document/install)，Mihomo [VLESS](https://wiki.metacubex.one/en/config/proxies/vless/) 与 [TLS/REALITY](https://wiki.metacubex.one/en/config/proxies/tls/)。

## 0. 建立任务与恢复点

先读 [task-state.md](task-state.md)，运行：

```bash
python3 scripts/init_task.py --root ./vpn-vps-work --name <task-slug>
```

完成需求卡、决策记录和授权状态。确认供应商 console/rescue 可用、SSH 主机指纹已核对，并从另一个终端证明备用公钥登录；否则不进入写阶段。

## 1. 远端 precheck（只读）

从 skill 根目录执行，保留输出：

```bash
ssh -p <SSH_PORT> <ADMIN_USER>@<VPS_IP> \
  'sudo bash -s -- --reality-port 443' \
  < scripts/remote_preflight.sh \
  | tee <task-dir>/evidence/remote-preflight.txt
```

`FAIL` 必须解决；`WARN` 必须在决策记录中接受或解决。尤其检查端口占用、现有代理服务、防火墙类型、失败单元、时间同步和有效 SSH 配置。precheck 不证明供应商 console 或备用 SSH 已可用，这两项需要单独证据。

## 2. 固定版本并生成配置

从官方 release 与 checksum 页面选定版本。不要使用搜索摘要提供的下载 URL，不执行未审阅的一键脚本。用选定的 Xray 二进制生成 X25519 密钥，并为**每台物理设备**分别生成 UUID 与 short ID；把结果填入 `<task-dir>/private/reality-input.json` 的 `clients` 数组，不要放进命令行或聊天。每项格式如下，禁止两台设备共用认证材料：

```json
{
  "device_name": "<NON_IDENTIFYING_DEVICE_ID>",
  "platform": "desktop",
  "uuid": "<UNIQUE_UUID>",
  "short_id": "<UNIQUE_REALITY_SHORT_ID>"
}
```

REALITY `target` 必须先用当前 Xray 的 `tls ping` 和证书/SNI 行为核对。不要默认选择会把未认证流量转发到公共 CDN 的 target；若无法评估风险，停止并换目标或实现。

```bash
chmod 600 <task-dir>/private/reality-input.json
python3 scripts/render_reality_bundle.py \
  --input <task-dir>/private/reality-input.json \
  --output <task-dir>/private/rendered
```

渲染器会验证 IP、端口、每设备 UUID、X25519 key、每设备 short ID、域名、版本门禁和残留占位符。客户端结果位于 `<task-dir>/private/rendered/client/<device_name>/mihomo.yaml`；生成目录包含 Secret，不得压入分享包。

从 Mihomo 官方 release 获取与输入版本、客户端平台/架构一致的二进制并核对官方 SHA-256；不要使用系统里碰巧存在的未知版本。用真实解析器检查每台设备配置：

```bash
python3 scripts/validate_mihomo_bundle.py \
  --bundle <task-dir>/private/rendered \
  --mihomo-bin <verified-mihomo-binary> \
  --output <task-dir>/evidence/mihomo-validation.json
```

检查器会核对二进制版本与 manifest、对每个配置运行 `mihomo -t -f`，并记录二进制、manifest 与配置 SHA-256。任一文件失败或检查后发生变化，状态机都拒绝进入 `rendered`。命令成功只证明该 Mihomo 内核接受语法，仍不能替代 Android/桌面实际导入和流量验收。

保存 precheck 证据并完成渲染后，按 [task-state.md](task-state.md) 依次推进到 `preflight` 和 `rendered`；脚本会拒绝缺少证据的推进。

## 3. 上传、计划与部署

把官方 Xray ZIP、渲染目录及部署脚本上传到服务器的专用临时目录。先运行 plan；它会验证 SHA-256、归档内二进制版本、渲染计划版本和 Xray 配置语法，但不会写系统：

```bash
sudo bash deploy_reality.sh \
  --bundle <remote-rendered-dir> \
  --archive <remote-xray-zip> \
  --sha256 <OFFICIAL_SHA256> \
  --plan
```

确认 plan、恢复控制台和备用 SSH 后，单独授权 apply：

```bash
sudo env ACK_RECOVERY_CONSOLE=yes ACK_SSH_BACKUP_LOGIN=yes \
  bash deploy_reality.sh \
  --bundle <remote-rendered-dir> \
  --archive <remote-xray-zip> \
  --sha256 <OFFICIAL_SHA256> \
  --apply
```

把 apply 的完整标准输出保存为 `<task-dir>/evidence/deploy.txt`。若在本机通过 SSH 调用远端脚本，应在本机管道末尾使用 `tee`，确保其中同时保留 `DEPLOY_RESULT=PASS` 和精确 `BACKUP_DIR=`；不要只复制终端最后一行。

脚本只安装 Xray、root/xray 可读的配置和 hardened systemd unit；不改变 SSH、防火墙或重启主机。它在 `/var/backups/vpn-vps-lifecycle/reality-<UTC>` 保存先前 binary/config/unit 与服务状态。apply 后的语法、active 或 TCP 监听检查失败时自动恢复。

## 4. 防火墙分阶段实施

根据 precheck 检出的**现有**防火墙选择 UFW、nftables 或供应商安全组；不要同时引入第二套管理器。先保存完整规则，先允许当前 SSH TCP 端口，再允许 REALITY TCP 端口；在新终端重复 SSH 登录后才启用默认拒绝或删除旧规则。

UFW 示例仅适用于已经确认使用 UFW 的 Ubuntu：

```bash
sudo ufw status numbered
sudo ufw allow <SSH_PORT>/tcp comment 'vpn-vps-lifecycle ssh'
sudo ufw allow 443/tcp comment 'vpn-vps-lifecycle reality'
sudo ufw status numbered
```

如果 UFW 尚未启用，`ufw enable` 是独立高风险步骤，需要再次确认 console 和备用 SSH。回滚时先恢复 SSH 可达，再按实际规则编号删除本次新增项；不要使用 `ufw reset`。

## 5. Server postcheck

```bash
sudo bash remote_verify.sh --port 443 \
  | tee <task-dir>/evidence/remote-verify.txt
```

`REMOTE_VERIFY_RESULT=PASS` 只证明服务端。它不能证明 REALITY 握手、客户端 DNS、出口 IP、规则/全局模式或用户网站。

若要主动回滚，先 plan 再 apply，使用部署输出的精确目录：

```bash
sudo bash rollback_reality.sh --backup <BACKUP_DIR> --plan
sudo bash rollback_reality.sh --backup <BACKUP_DIR> --apply
```

回滚会恢复原 binary/config/unit 和服务状态；若 `xray` 用户、组、`/etc/xray` 或 `/var/lib/xray` 是本次部署创建的，也会尝试移除。目录只在为空时移除，绝不递归删除；非空或仍被占用时会输出 WARN、标记 `ROLLBACK_RESULT=PARTIAL` 并安全保留，必须人工核对，状态机也不会把它当成完整回滚。把主动回滚输出保存到 `<task-dir>/evidence/rollback.txt`，只有 PASS 才推进 `rolled-back`。回滚后重新运行服务、监听、SSH 和客户端检查。

## 6. Mihomo 客户端与自循环

把每个 `<device_name>/mihomo.yaml` 只导入对应设备，不跨设备复制。桌面模板同时包含管理 IP 的 `DIRECT` 规则和 TUN `route-exclude-address`；Android 模板明确包含 `GLOBAL` 与 `PROXY`，避免规则模式无组或全局组没有叶子节点。

验收顺序：语法检查、重新导入、规则模式、全局模式明确选 `Reality-node`、出口 IP、目标网站、SSH 管理路由、Wi-Fi/蜂窝切换和应用重启。不能只看 VPN 图标或 `systemctl active`。

## 7. 自动化网站样本与 burn-in

把真实业务 URL 写入权限 0600 的 `<task-dir>/private/acceptance-urls.txt`，从已启动的本地 Mihomo mixed port 运行：

```bash
python3 scripts/client_acceptance.py \
  --proxy http://127.0.0.1:7890 \
  --urls-file <task-dir>/private/acceptance-urls.txt \
  --expected-exit-file <task-dir>/private/expected-exit-ip.txt \
  --repeat 3 \
  --output <task-dir>/evidence/client-acceptance.json
```

先把预期 VPS 出口地址单独写入 `expected-exit-ip.txt` 并保持权限 0600，避免把真实管理地址暴露在进程参数中。脚本通过可信 IP 回显 endpoint **强制比较**观察出口与预期值，不一致即非零退出；它还记录 curl 经本地代理看到的客户端侧 DNS/connect/TLS/TTFB/total 与 HTTP 状态，其中 `curl_connection_remote_ip` 可能是代理端点，不能误称为目标站 IP。GET 成功不能替代登录、播放、API 或支付等完整业务验收。按 [acceptance.md](acceptance.md) 覆盖多个晚高峰并控制流量预算。

另外把规则模式、全局模式和 SSH 自循环人工结果保存到 `evidence/manual-client-checks.txt`：

```text
rule_mode=PASS
global_mode=PASS
ssh_loop=PASS
```

三项和 JSON 出口门禁全部通过后才推进 `client-tested`。

## 完成门禁

只有以下证据同时存在才能把该切片标记 `accepted`：precheck、版本/校验值、渲染 manifest、部署 backup 路径、server postcheck、真实设备握手与出口、规则和全局模式、SSH 无自循环、目标业务、授权重启后的复验（若用户授权重启），以及约定周期的 burn-in。任何缺失项保持为 `not yet proven`。
