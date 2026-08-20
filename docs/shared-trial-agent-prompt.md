# SRE Agent 靶场试用 Prompt

你将参加一次 SRE 故障诊断评测。请直接使用下列平台连接信息完成测试，不要要求使用者提供回调地址、kubeconfig 或模型 API Key。

```text
Base URL: https://sre-lab.8dgerunner.xyz
Authorization: Bearer <由平台管理员私下提供的试用 Token>
```

这是可撤销的共享实验 Token，仅用于初期试用。不要把它写入代码仓库、长期日志或其他系统；以后收到个人 Token 时，只替换上面的 Bearer Token。

## 任务

1. 调用 `GET /v1/cases` 查看当前案例，选择一个尚未完成的案例；没有偏好时优先选择非 `t001` 案例。
2. 调用 `POST /v1/runs` 创建独立评测：

```json
{"case_id":"<case_id>","agent_id":"trial-agent-<当前时间戳>"}
```

3. 只根据平台返回的告警背景和观测证据诊断，不搜索或读取 RCA100 answer key。
4. 通过 `POST /v1/runs/{run_id}/tools` 自主调用只读工具：
   `get_alerts`、`get_topology`、`query_metrics`、`search_logs`、`query_traces`、`list_events`。
5. 所有结论必须引用工具实际返回的 `evidence_id`；不要编造证据。
6. 调用 `POST /v1/runs/{run_id}/answer` 提交：

```json
{
  "root_cause_entities": ["<根因实体>"],
  "fault_type": "<故障类型>",
  "causal_steps": ["<按传播顺序排列的节点>"],
  "evidence_ids": ["<真实 evidence_id>"],
  "summary": "<简洁诊断结论>",
  "remediation_proposal": {
    "action": "<建议动作>",
    "validation": "<验证方法>",
    "rollback": "<回滚方法>"
  }
}
```

7. 调用 `GET /v1/runs/{run_id}` 获取最终状态和评分。

## 请求规则

- 每个请求都携带 `Authorization: Bearer <Token>` 和 `Content-Type: application/json`。
- Agent 只调用平台 HTTPS API，不访问集群、宿主机或 Chaos Mesh 控制面。
- 不执行修复；只提交修复提案。
- 工具报错时调整参数继续，禁止尝试越权接口。
- 总用时控制在 20 分钟内，避免无目的重复调用。

## 最终只返回

```text
案例：
Run ID：
根因：
故障类型：
关键证据：
修复建议：
得分：
用时 / 工具调用次数：
```
