# SRE Lab Agent API

这是给外部 Agent 使用的接口。网页只是可选的人类演示入口；同事的 Agent
直接调用 HTTPS API，不需要暴露 Agent 地址，也不需要把模型 API Key 交给平台。

## 接入信息

```text
Base URL: https://sre-lab.8dgerunner.xyz
认证：Authorization: Bearer <participant-token>
```

API Token 只用于 Agent 接入。人类试用请使用网页账号登录，不要把 Token 发到群聊。

初期试用可直接使用 [共享试用 Prompt](shared-trial-agent-prompt.md) 中预置的可撤销
实验 Token；它只用于降低首次接入门槛。正式评测切换为每人、每 Agent 独立 Token，
替换 Prompt 中的 Bearer Token 即可。

管理员在网页左侧打开“管理接入 Token”：填写 Agent 名称、对应使用人、有效期和
最小权限。签发后网页一次性显示 Base URL 与 Token，可直接复制为 Agent 环境变量；
关闭后平台无法找回明文，只保存 SHA-256 哈希。网页可查看权限、到期时间、最后使用
时间、使用次数，并可立即撤销。默认有效期 7 天，最长 90 天。

对应的管理员 API 是：

```text
GET  /v1/admin/tokens
POST /v1/admin/tokens
POST /v1/admin/tokens/{token_id}/revoke
```

管理员 API 只接受网页登录后的 HttpOnly Cookie，不接受普通 Agent Token。

## Agent 工作流

```text
GET  /v1/cases                         选择案例
POST /v1/runs                          创建独立 run，领取任务背景
POST /v1/runs/{run_id}/tools           调用只读观测工具
POST /v1/runs/{run_id}/answer          提交诊断和证据
GET  /v1/runs/{run_id}                 获取评分与运行指标
```

### 1. 创建 run

```bash
curl -H "Authorization: Bearer $SRE_LAB_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"case_id":"t001","agent_id":"alice-agent"}' \
  https://sre-lab.8dgerunner.xyz/v1/runs
```

响应包含告警背景、时间窗口、可用观测工具和 `run_id`，不包含答案文件。

### 2. 观察证据

```json
{
  "tool": "query_traces",
  "arguments": {"service": "payment", "error_only": true, "limit": 20}
}
```

通过 `POST /v1/runs/{run_id}/tools` 发送。允许的工具是：
`query_metrics`、`search_logs`、`query_traces`、`list_events`、`get_alerts`、
`get_topology`。`get_topology` 不传 `entity` 时会自动使用当前告警实体。

### 3. 提交诊断

```json
{
  "root_cause_entities": ["payment"],
  "fault_type": "httpError5xx",
  "causal_steps": ["payment", "checkout", "checkout::/oteldemo.CheckoutService/PlaceOrder"],
  "evidence_ids": ["ev_..."],
  "summary": "payment 返回 5xx 并沿调用链传播到 checkout",
  "remediation_proposal": {}
}
```

平台只评估提案，不执行 Agent 的修复动作。评分包括根因实体、故障类型、因果链、
checkpoint 证据匹配、耗时、工具调用和拒绝调用。

## 并发和隔离

每次创建 run 都会获得独立的 `run_id`、证据集合、锁和报告；多个同事可以同时运行。
Agent 永远不会获得 kubeconfig、Chaos Mesh 凭据、宿主机访问权或 answer key。

## 最小客户端

仓库提供无第三方依赖的 [agent_client.py](/Users/tonalddrump/Documents/DuckLake/examples/agent_client.py)：

```bash
export SRE_LAB_TOKEN='由平台管理员私下发放的 Agent Token'
python examples/agent_client.py --case t001 --agent-id my-agent
```

示例中的固定答案仅用于连通性测试；实际使用时，把 `client.tool(...)` 返回的证据交给
同事自己的 Agent/LLM，再把 Agent 生成的最终 JSON 传给 `client.answer(...)`。

## Token 最佳实践

- 每个 Agent、每位同事使用独立 Token，不共享一个长期 Token。
- 权限按用途选择：`run:create`、`evidence:read`、`answer:submit`；普通完整评测需要三项。
- 默认短期有效，人员离开或 Agent 更换后立即撤销并重新签发。
- 明文只在签发响应显示一次；平台磁盘只保存哈希和元数据。
- Token 只放在 Agent 的 Secret Manager / 环境变量，不写入 prompt、日志或代码仓库。
- 共享试用 Prompt 是短期例外：仅使用低权限、短有效期、可随时撤销的实验 Token，
  不用于正式排名；个人 Token 启用后立即撤销共享 Token。
- 质量评分不依赖 Token；Token 只负责身份、审计和撤销。

## 当前边界

- 当前 Contabo 已部署的是 REST pull API；Agent 主动轮询平台，不需要回调地址。
- `/v1/turn` 是早期 push 协议草案，当前公网服务不依赖它，也不要把它当成接入入口。
- 当前已支持按 Agent 分配、独立审计和撤销的短期 Bearer Token；团队规模扩大后再接入统一身份系统。
