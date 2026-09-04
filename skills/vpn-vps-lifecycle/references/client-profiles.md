# Clash Meta / Mihomo 客户端

客户端文件含凭据，必须在 skill 和版本库外生成，权限 0600；每台设备一组凭据。分享文档只列模板字段和非秘密校验结果。

REALITY 纵向切片从 `reality-input.json` 的 `clients` 数组按设备生成 `private/rendered/client/<device_name>/mihomo.yaml`。每个 `device_name`、UUID 和 short ID 必须唯一；只把该目录下的文件交给对应设备，不能把桌面配置复制给手机或让两台设备共用凭据。

本文件只用于 Clash Meta/Mihomo 的 HY2 与 VLESS/REALITY 配置。若用户选择 WireGuard，应使用受支持的 WireGuard 客户端或系统集成，按 peer 生成独立配置，并单独验收路由、DNS、IPv4/IPv6 和 kill-switch；不要把 WireGuard 强塞进这些 Clash 模板。

## 桌面端防代理回环

当桌面端启用 TUN 时，管理 IP 需要两层绕过：

```yaml
tun:
  route-exclude-address:
    - <VPS_IP>/32

rules:
  - IP-CIDR,<VPS_IP>/32,DIRECT,no-resolve
```

`DIRECT` 规则只处理规则引擎；全局 TUN 仍可能先把 SSH 包送进代理，因此不能省略 route exclusion。修改活动配置前先备份，不静默切换用户当前选择器。

## Android 的 GLOBAL 与规则组

Clash Meta for Android 需要显式 `GLOBAL`，并把规则模式组作为它的成员；仅在 YAML 其他位置定义 `AUTO` 和 `PROXY` 可能导致规则模式显示“没有可以显示的组”。保持可用叶子节点在前，避免默认落到 `DIRECT`：

```yaml
proxy-groups:
  - name: GLOBAL
    type: select
    proxies:
      - Reality-node
      - HY2-node
      - PROXY
      - AUTO

  - name: AUTO
    type: fallback
    proxies:
      - HY2-node
      - Reality-node
    url: https://www.gstatic.com/generate_204
    interval: 300
    lazy: true

  - name: PROXY
    type: select
    proxies:
      - AUTO
      - HY2-node
      - Reality-node
      - DIRECT

rules:
  - MATCH,PROXY
```

不要让 `PROXY` 或 `AUTO` 反向引用 `GLOBAL` 形成循环。

## 验收

1. 用 [deployment-reality-mihomo.md](deployment-reality-mihomo.md) 的 `validate_mihomo_bundle.py` 对完整配置运行 **manifest 指定版本** Mihomo 的真实语法检查；不要用 YAML 能解析或文本包含组名代替内核检查。
2. 删除旧导入副本、重新导入并启动；只切换模式不能证明源文件已重新加载。
3. 全局模式分别选择 HY2 和 REALITY，验证可访问目标站点并返回正确出口 IP。
4. 规则模式必须显示预期的 `PROXY`，并验证 `MATCH,PROXY` 的真实流量。
5. Android 代理页面的模式切换通常是 session override；需要持久模式时在 Override/Mode 中设置并彻底重启应用验证。
6. 对长期在线手机测试锁屏/后台、Wi-Fi 与蜂窝切换、应用重启和授权后的设备重启。VPN 图标不代表用户态代理仍处理流量。
7. `Block connections without VPN` 是 fail-closed lockdown，不是通用稳定性选项；只有用户明确要求且已有恢复路径时启用。

示例文件位于 [../assets/clash-meta-desktop.example.yaml](../assets/clash-meta-desktop.example.yaml) 和 [../assets/clash-meta-android.example.yaml](../assets/clash-meta-android.example.yaml)。其中使用文档保留地址和假凭据，必须替换。
