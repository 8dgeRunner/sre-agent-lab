# SRE Agent Lab

一个面向 SRE Agent 的安全故障诊断靶场：用可复现的故障证据、受控工具和确定性评分，练习根因分析，而不接触生产数据或集群权限。

## 运行模式

| 模式 | 输入 | 是否需要 k3s / Chaos Mesh | 作用 |
| --- | --- | --- | --- |
| 离线评测 | RCA100 保存的 metrics、logs、traces、events、topology | 否 | Agent 查询历史故障证据，并与隐藏 Ground Truth 对比评分；不是猜测 |
| Live 靶场 | k3s 合成服务的实时观测数据 | 是 | Chaos Mesh 注入故障，Agent 诊断实时症状并评分 |

两种模式共用 Agent API、工具 allowlist 和评分器。离线模式不产生新故障；要练习 Kubernetes 故障注入，必须先部署 k3s、Chaos Mesh 和观测组件。

## 快速开始：离线评测

```bash
uv sync
uv run pytest
uv run python -m sre_lab.serve \
  --case-root data/rca100 \
  --ground-truth-root data/rca100/answer_key
```

RCA100 原始数据和答案文件因授权与防泄漏原因不随仓库发布。运行离线案例前，请将获得授权的数据放入 `data/rca100/`。答案文件只能由评分器读取，不能提供给 Agent。

## Live 靶场

部署顺序：

1. 准备独立的 k3s 集群和 `chaos-lab` namespace。
2. 单独安装 Chaos Mesh，并应用 [`deploy/chaos-lab/`](deploy/chaos-lab/) 中的安全基线。
3. 部署合成工作负载和观测组件。
4. 通过 [`sre_lab/chaosmesh.py`](sre_lab/chaosmesh.py) 创建、查询、停止和清理实验。

Chaos Mesh 只负责故障注入；控制面负责场景生命周期、证据收集、Agent 协议和评分。Live 场景必须先通过症状契约，才允许进入 Agent 评测。

## Agent 接入

平台只向 Agent 暴露 HTTPS API 和只读工具，不提供 kubeconfig、Chaos Mesh 凭据、宿主机访问权或答案文件。协议和示例见：

- [`docs/agent-protocol.md`](docs/agent-protocol.md)
- [`examples/agent_client.py`](examples/agent_client.py)

每个 Run 独立隔离并可审计，支持多个 Agent 并发；平台不托管参与者的模型 API Key。

## 给 Agent 的入口

- 需要修改或维护本仓库：先读 [`AGENTS.md`](AGENTS.md)。
- 需要参加 SRE 故障诊断：读 [`docs/agent-quickstart.md`](docs/agent-quickstart.md)，按 API 流程运行一个独立 Run。

Agent 不应读取 `data/rca100/answer_key/`、猜测证据 ID、访问集群控制面或执行自动修复。

## 来源与边界

- [RCA100 / AIOps benchmark](https://www.aiops.cn/gitlab/aiops-live-benchmark/agenticopseval)：案例结构和 Ground Truth 格式参考该项目；数据遵循上游 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)，本仓库不再分发原始数据。
- [Chaos Mesh](https://github.com/chaos-mesh/chaos-mesh)：Live 故障注入依赖其 API/CRD，遵循上游 [Apache-2.0](https://github.com/chaos-mesh/chaos-mesh/blob/master/LICENSE)。

本仓库**不是 Chaos Mesh 的 fork**，不包含 Chaos Mesh 源码；这里只提供 Python 适配器、场景清单和安全策略。ChaosBlade 不属于本项目。首期不包含生产接入、宿主机级故障、自动修复和 FDB Simulation。
