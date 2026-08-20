# SRE Agent Quickstart

本文面向参加故障诊断评测的 Agent，不是仓库代码修改指南。

## 1. 选择模式

- **远程评测**：使用平台管理员提供的 HTTPS `Base URL` 和 Bearer Token；不需要 kubeconfig、k3s 或 Chaos Mesh。
- **本地离线评测**：使用授权的 RCA100 证据文件；答案文件只由评分器读取。
- **Live 靶场**：只有平台管理员启动 k3s、Chaos Mesh 和合成工作负载后才可进行；Agent 仍只调用平台 API。

## 2. 远程评测流程

1. `GET /v1/cases` 获取可用案例。
2. `POST /v1/runs` 创建独立 Run。
3. 仅调用返回的只读工具：`get_alerts`、`query_metrics`、`search_logs`、`query_traces`、`list_events`、`get_topology`。
4. 只引用工具实际返回的 `evidence_id`，按时间和传播关系形成根因链。
5. `POST /v1/runs/{run_id}/answer` 提交根因实体、标准故障类型、因果链和证据。
6. `GET /v1/runs/{run_id}` 获取评分和运行指标。

## 3. 评分重点

评分关注根因实体、故障类型、因果链覆盖和证据正确性。工具调用次数和耗时单独记录，不用低成本掩盖错误诊断。

## 4. 禁止事项

- 不读取或猜测 answer key。
- 不伪造 evidence ID 或引用未返回的证据。
- 不调用未列出的工具，不访问 Kubernetes/Chaos Mesh 控制面。
- 不执行修复；只提交包含验证和回滚步骤的提案。

完整请求字段和示例见 [`agent-protocol.md`](agent-protocol.md) 与 [`../examples/agent_client.py`](../examples/agent_client.py)。
