# 首次登录与系统安全基线

目标是防止锁死并得到可回滚、可重启的 Ubuntu 基线。默认先只读检查；任何改变 SSH、网络、防火墙或重启的动作都需要明确授权。

## 建立恢复路径

1. 在供应商面板确认 VNC/console、reinstall/rescue 和密码恢复可用。
2. 从独立面板或 VNC 获取 SSH 主机指纹；首次连接后核对，不使用 `StrictHostKeyChecking=no`。
3. 如果本机启用 Clash/Mihomo TUN，在依赖 SSH 前让管理 IP 同时绕过规则层和 TUN 路由层。
4. 记录 OS、实例规格、管理端口、当前登录方式和 cloud-init 状态，但不把凭据写入文件。

## 只读发现

Ubuntu 目标可先运行 [../scripts/remote_preflight.sh](../scripts/remote_preflight.sh) 并把输出保存到任务 `evidence/`。下面命令仍用于补充检查，不能用聊天摘要替代原始证据。

按系统实际能力检查：

```bash
uname -a
cat /etc/os-release
cloud-init status --wait
systemctl --failed
timedatectl
ss -lntup
df -hT
df -i
free -h
lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS,ROTA
ip -br address
ip route
sshd -T
```

检查软件源、待更新包、启动错误、NTP、磁盘/inode、内存、Swap、虚拟化、网卡错误与当前防火墙。guest 看见的虚拟设备不能证明物理 DDR 或 SSD 后端。

## 分阶段实施

### Prepare

- 为每个将修改的配置创建 root-only 时间戳备份，并先写明回滚命令。
- 完成安全更新，安装最少依赖，建立非 root 管理用户和独立 SSH key。
- 验证该用户从新的终端完成 key-only 登录和 `sudo`。
- 配置主机名、时区/NTP、自动安全更新、适量 Swap，以及适合当前内核与网络的 BBR/fq。
- 不在此阶段删除供应商初始入口。

### Lockdown

只有备用登录已经通过后才：

- 禁止 root SSH 和密码认证，保留公钥认证。
- 验证 `sshd -t` 和 `sshd -T`，使用 reload 优先于不必要的 restart。
- 建立默认拒绝入站的最小防火墙，只放行管理端口和明确部署的 TCP/UDP 服务。
- 启用 Fail2ban 或等效防护，并确认没有误封当前管理路径。

### Reboot acceptance

重启需单独授权。重启后重新检查：主机指纹、管理员登录、sudo、网络、NTP、Swap、内核参数、防火墙、Fail2ban、失败单元和启动日志。

## 备份与 Secret

- 配置备份应为 root-only，且不进入共享目录或版本库。
- 私钥永不上传服务器；服务器只保存公钥。
- 不在命令行参数中直接放置会进入 shell history/process list 的 Secret。
- 终端输出、日志和验收报告只记录权限、路径和校验状态，不打印内容。
