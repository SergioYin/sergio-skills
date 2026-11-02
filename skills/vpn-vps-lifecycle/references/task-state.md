# 可恢复、证据门禁的任务状态

长流程不得只依赖聊天上下文。先在 skill 外创建权限受限的任务目录：

```bash
python3 scripts/init_task.py --root ./vpn-vps-work --name <task-slug>
```

目录约定：

```text
<task>/
├── state.json                 # 固定阶段、授权状态和审计历史；不放 Secret
├── public/                    # 需求卡、决策记录、声明矩阵；分享前仍需脱敏
├── private/                   # 输入、每设备客户端配置和真实网站清单，0600
│   └── rendered/              # 生成的服务端/客户端 bundle，含 Secret
├── evidence/                  # precheck/postcheck/路由/测速证据
│   └── burn-in/windows/       # 逐窗口封存证据，0400、禁止覆盖
└── reports/                   # 验收报告
```

任务目录已存在且含有效 `state.json` 时，初始化脚本只报告恢复点，不覆盖文件。查看状态：

```bash
python3 scripts/update_state.py --task <task-dir> status
```

## 授权记录

只有用户在当前任务中明确授权后，agent 才能记录授权；脚本不能替代真实授权。证据引用只写不含 Secret 的消息 ID、工单 ID 或人工说明，不复制凭据：

```bash
python3 scripts/update_state.py --task <task-dir> authorize \
  --kind deploy --value true --evidence <current-user-authorization-reference>
```

`purchase`、`deploy`、`reboot`、`test-traffic` 分别记录，不能互相替代，也不能继承别的任务或历史聊天。`test-traffic` 授权还必须与 plan 的字节预算一致；用户撤销时以 `--value false` 记录新的证据。

## 固定阶段与命令

只能按以下状态机推进，不能自由填写阶段：

```text
interview → research → plan-confirmed → preflight → rendered
→ server-deployed → client-tested → burn-in → accepted
                         └──────────────→ rolled-back → preflight
                                          ↑
                    client-tested / burn-in
```

每次只推进一步：

```bash
python3 scripts/update_state.py --task <task-dir> advance --to <next-phase>
```

脚本会原子更新 `state.json` 并追加时间化历史。主要门禁：

- `plan-confirmed`：需求卡和决策记录的必填占位符已完成。
- `rendered`：`remote-preflight.txt` 明确 PASS；若为 WARN，还要有非空的 `preflight-warnings-accepted.txt`；渲染 manifest 至少含一个客户端，并且每个配置均由 manifest 指定的真实 Mihomo 二进制检查通过。配置或 manifest 变更会使旧检查失效。
- `server-deployed`：当前任务已有 deploy 授权证据，`deploy.txt` 同时含 `DEPLOY_RESULT=PASS` 与 `BACKUP_DIR=`，且 `remote-verify.txt` 为 PASS。
- `client-tested`：`client-acceptance.json` 的 `failures=0` 且 `exit_ip_match=true`，人工证据同时含 `rule_mode=PASS`、`global_mode=PASS`、`ssh_loop=PASS`。
- `burn-in`：已有当前任务的 `test-traffic` 明确授权证据；`private/burn-in-plan.json` 记录用户批准时间、IANA 时区、晚高峰、至少三个不同日期、客户端/服务端采样对齐范围、测试字节预算和资源阈值。
- `accepted`：`summarize_burn_in.py` 根据 `evidence/burn-in/windows/*.json` 重新计算的 summary 为 PASS，且与状态机现场重算完全一致；验收报告不再含占位符。人工手写 `result: PASS` 会被拒绝。
- `rolled-back`：`rollback.txt` 明确含 `ROLLBACK_RESULT=PASS`。

命令运行过、进程 active、VPN 图标出现或某一个网站可开都不能绕过这些门禁。失败时保留失败证据与当前阶段；修复后重新生成相应证据，不手工篡改 `state.json`。
