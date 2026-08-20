from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo-dir", required=True, type=Path)
    parser.add_argument("--output-root", default="reports/leadership", type=Path)
    args = parser.parse_args()
    d = args.demo_dir
    run = load(d / "run.json")
    result = load(d / "result.json")
    issued = load(d / "issued.json")
    run_id = run["run_id"]
    out = args.output_root / run_id
    raw = out / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    copied_files = []
    for source in sorted(d.glob("*.json")):
        if source.name in {"issued.json", "admin-login.json", "answer.json"}:
            continue
        target = raw / source.name
        shutil.copy2(source, target)
        copied_files.append(target)

    artifact_manifest = {
        "run_id": run_id,
        "files": [
            {
                "path": f"raw/{path.name}",
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in copied_files
        ],
    }
    (out / "artifact-manifest.json").write_text(
        json.dumps(artifact_manifest, ensure_ascii=False, indent=2) + "\n"
    )

    tool_files = [
        ("get_alerts", "alerts.json"), ("get_topology", "topology.json"),
        ("payment error_count", "payment-error-count.json"),
        ("payment error_rate", "payment-error-rate.json"),
        ("checkout error_count", "checkout-error-count.json"),
        ("checkout error_rate", "checkout-error-rate.json"),
        ("operation error_count", "operation-error-count.json"),
        ("operation error_rate", "operation-error-rate.json"),
        ("query_traces", "traces.json"), ("search_logs", "logs.json"),
    ]
    counts = []
    for label, filename in tool_files:
        payload = load(d / filename)
        counts.append(f"| `{label}` | {len(payload.get('evidence', []))} | `{filename}` |")

    score = result["score"]
    metrics = result["metrics"]
    started = (d / "started_at.txt").read_text().strip()
    finished = (d / "finished_at.txt").read_text().strip()
    status_after_revoke = (d / "after-revoke-status.txt").read_text().strip()
    report = f"""# SRE Agent 靶场：Mac 外部 Agent 完整演示报告

> 目的：让领导看到“平台提供故障背景和观测工具，外部 Agent 负责分析，平台负责可重复评分”的完整闭环。

> **审计声明：本次是流程验收，不是盲测。** 执行者所在工作区可访问 RCA100 ground truth，
> 因此下面的 90 分只能证明 API、证据、评分、报告和 Token 生命周期可用，不能用于比较 Agent 准确率。

## 一页结论

- **Agent 主机：** 本地 Mac；**靶场平台：** Contabo HTTPS API。
- **案例：** `t001` / checkout 错误次数告警。
- **流程验收结论：** 提交根因 `payment`、故障类型 `httpError5xx` 和完整因果链，评分器按规则返回结果。
- **评分：** `{score['total']}/100`；实体和故障类型均为 100%，证据命中 `4/6`。
- **安全闭环：** 为本次 Mac Agent 签发独立 Token，完成后撤销；撤销后 API 返回 HTTP `{status_after_revoke}`。

## 给领导看的流程

```mermaid
flowchart LR
  A[Mac 上的 Agent] -->|Bearer Token| B[Contabo 平台 API]
  B --> C[领取 t001 背景]
  C --> D[调用只读 metrics/logs/traces/topology]
  D --> E[Agent 形成根因与证据]
  E --> F[提交答案]
  F --> G[确定性评分与报告]
  B --> H[审计 Token / Run / 工具调用]
```

网页只是人类演示入口；参与者的 Agent 直接使用 REST API。

## API 全行程索引

| 顺序 | 调用 | 用途 | 本次结果 |
|---:|---|---|---|
| 1 | `POST /v1/login` | 管理员登录网页 | 成功，获得 HttpOnly 会话 |
| 2 | `POST /v1/admin/tokens` | 为 Mac Agent 签发独立 Token | 成功，明文仅出现一次 |
| 3 | `GET /v1/cases` | 获取可评测案例 | 返回 `t001` |
| 4 | `POST /v1/runs` | 创建隔离 Run、领取任务 | 返回 `{run_id}` |
| 5 | `POST /v1/runs/{{run_id}}/tools` × 10 | 查询告警、拓扑、指标、Trace 和日志 | 全部成功，拒绝 0 次 |
| 6 | `POST /v1/runs/{{run_id}}/answer` | 提交根因、因果链和 evidence ID | 返回评分 `{score['total']}/100` |
| 7 | `POST /v1/admin/tokens/{{token_id}}/revoke` | 撤销本次 Token | 成功 |
| 8 | `GET /v1/cases`（使用已撤销 Token） | 验证撤销即时生效 | HTTP `{status_after_revoke}` |

## 本次实际行程

### 1. 签发身份

- 管理员通过网页登录后创建 Agent Token。
- Token 名称：`{issued['name']}`
- Token ID：`{issued['token_id']}`
- 有效期：1 天（明文未写入本报告）。

### 2. 领取案例

```text
POST /v1/runs
case_id=t001
agent_id=mac-codex-leadership-demo
run_id={run_id}
```

平台返回告警标题、告警实体、时间窗口、允许工具；没有返回 answer key、kubeconfig 或 Chaos Mesh 凭据。

### 3. 观测调用

| 工具 | 返回证据数 | 原始记录 |
|---|---:|---|
{chr(10).join(counts)}

关键证据：

- payment `error_count=8899`，超过 ground truth 的 `8829` 阈值。
- payment `error_rate=49.6457%`，命中根因 checkpoint。
- checkout `error_count=8891`、`error_rate=49.6513%`，说明错误传播。
- Trace/日志均出现 `Payment request failed. Invalid token`。
- Topology 证据确认 checkout 调用 payment。

### 4. Agent 提交

```json
{{
  "root_cause_entities": ["payment"],
  "fault_type": "httpError5xx",
  "causal_steps": ["payment", "checkout", "checkout::/oteldemo.CheckoutService/PlaceOrder"],
  "evidence_ids": ["平台实际返回的 evidence_id"]
}}
```

平台只评分诊断提案，不执行修复。

## 评分解释

| 指标 | 结果 |
|---|---:|
| 根因实体 | {score['entity']*100:.0f}% |
| 故障类型 | {score['fault']*100:.0f}% |
| 因果链覆盖 | {score['chain_coverage']*100:.0f}% |
| 证据 precision | {score['evidence_precision']*100:.0f}% |
| 证据 recall | {score['evidence_recall']*100:.1f}% |
| checkpoint 命中 | {score['matched_checkpoints']}/{score['total_checkpoints']} |
| 总分 | **{score['total']}/100** |

本次没有把分数伪装成满分：实体、类型和因果链命中，但 evidence matcher 将部分 checkout operation 证据归入传播 checkpoint，导致还有 2 个 checkpoint 未覆盖。由于这是非盲流程验收，该分数不能作为模型能力结论。

## 运行效率与安全

- 墙钟耗时：`{metrics['wall_time_seconds']}` 秒。
- 工具调用：`{metrics['tool_calls']}` 次；拒绝调用：`{metrics['rejected_calls']}` 次。
- Token usage：`{json.dumps(metrics.get('usage', {}), ensure_ascii=False)}` 是流程验收使用的自报示例字段，不是供应商账单，不参与质量排名。
- Token 在 `{started}` 签发，在 `{finished}` 之后撤销；撤销后 API HTTP `{status_after_revoke}`。

## 领导应理解的边界

1. 平台提供确定性的故障背景、证据工具和评分，不托管参与者的模型 API Key。
2. Agent 可以使用参与者自己的 LLM、规则引擎或工作流；平台不需要 Agent 回调地址。
3. 评分重点是“是否找对根因、是否引用正确证据、过程是否可审计”，Token 数量和模型费用不影响质量分。
4. 当前首期只评估诊断和修复提案，不自动执行修复。

## 独立 Agent 盲测状态

本次另外从一个干净临时目录启动了本机 Codex CLI，并明确禁止读取数据集或 answer key。
该进程成功创建独立 run 并调用了部分观测 API，但本机配置的模型代理持续出现模型目录解析和
response stream 中断，未能提交最终答案。该 run 的 Token 已撤销，因此没有把不完整结果计入成绩。

正式 Agent 排名必须在隔离工作目录或独立主机执行，并确保 Agent 无法读取本地 answer key。

## 重放命令（不包含任何秘密）

```bash
export SRE_LAB_TOKEN='<管理员网页签发的 Agent Token>'
python examples/agent_client.py \\
  --base-url https://sre-lab.8dgerunner.xyz \\
  --case t001 \\
  --agent-id my-agent
```

## 审计材料

- 原始 API 响应保存在本报告目录的 `raw/`。
- `artifact-manifest.json` 记录每个原始响应的字节数和 SHA-256，可验证材料未被替换。
- 本报告没有保存明文 Token。
- 运行 ID：`{run_id}`。
"""
    (out / "leadership-report.md").write_text(report)
    summary = f"""# SRE Agent 靶场｜参与者接入说明

## 一句话

参与者只需拿到平台管理员签发的短期 Token，让自己的 Agent 调用 HTTPS API；平台提供故障证据并返回可审计评分，不接触参与者的模型 API Key。

## 实测结果

| 项目 | 结果 |
|---|---|
| 环境 | Agent：本地 Mac；平台：Contabo |
| 案例 | `t001`：checkout 5xx |
| 诊断 | 根因 `payment`；类型 `httpError5xx` |
| 评分 | `{score['total']}/100`（流程验收，非盲测） |
| 运行 | `{metrics['tool_calls']}` 次观测调用；拒绝 `{metrics['rejected_calls']}` 次 |
| 安全 | Token 完成后撤销；撤销后 HTTP `{status_after_revoke}` |

## 参与者接入（管理员提供地址）

1. 管理员网页：打开“管理接入 Token”。
2. 填写 Agent 名称、使用人、有效期和权限，签发 Token。
3. 只显示一次，私下交付；参与者配置：

```bash
export SRE_LAB_URL=https://sre-lab.8dgerunner.xyz
export SRE_LAB_TOKEN='<管理员私下提供>'
python examples/agent_client.py --base-url "$SRE_LAB_URL" --case t001 --agent-id my-agent
```

## Agent 做什么

```text
领取案例 → 查询只读指标/日志/Trace/拓扑 → 提交根因与 evidence_id → 获得评分
```

评分看：根因实体、故障类型、因果链、证据正确性；Token 数量和自报 Token 消耗不参与质量排名。每个 Run 独立，支持多人并发。

## 边界

本次 `{score['total']}/100` 证明链路、评分和安全流程可用，不代表模型准确率；正式排名需在隔离工作区进行盲测。平台不执行 Agent 修复动作。

详细 API 原始记录见同目录 `leadership-report.md`、`raw/` 和 `audit.json`。
"""
    (out / "leadership-summary.md").write_text(summary)
    audit = {
        "run_id": run_id, "case_id": run.get("task", {}).get("task_id", "t001"),
        "agent_id": run.get("agent_id", "mac-codex-leadership-demo"),
        "evaluation_mode": "process_validation", "blind_test": False,
        "score_rankable": False,
        "token_id": issued["token_id"], "token_plaintext_recorded": False,
        "token_revoked_verified": int(status_after_revoke) == 401,
        "score": score, "metrics": metrics, "started_at": started, "finished_at": finished,
        "after_revoke_http": int(status_after_revoke),
        "tool_sequence": [label for label, _filename in tool_files],
        "artifact_manifest": "artifact-manifest.json",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (out / "audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
    print(out / "leadership-report.md")


if __name__ == "__main__":
    main()
