from __future__ import annotations

import json
import re
from pathlib import Path

from .models import AgentConclusion, RcaScore


def write_report(
    output: str | Path, conclusion: AgentConclusion, score: RcaScore, ground_truth: dict
) -> tuple[Path, Path]:
    markdown_path = Path(output)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path = markdown_path.with_suffix(".json")
    payload = {
        "conclusion": conclusion.to_dict(),
        "score": score.to_dict(),
        "ground_truth": ground_truth,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n")

    markdown = _compact_markdown(conclusion, score)
    markdown_path.write_text(markdown)
    return markdown_path, json_path


def _short_value(item) -> str:
    value = str(item.value).replace("\n", " ")
    if item.source == "metric":
        return f"{item.entity} 的 {item.signal} = {value[:40]}"
    if item.source in {"trace", "log"}:
        match = re.search(r"(?i)invalid token|exception|error", value)
        if match:
            start = max(0, match.start() - 35)
            return value[start : start + 150].strip()
        return value[:140]
    if item.source == "alert":
        current = re.search(r'current_value["\']?\s*[:=]\s*["\']?([0-9.]+)', value)
        return f"{item.entity} 告警" + (f"，当前值 {current.group(1)}" if current else "触发")
    if item.source == "topology":
        return item.detail.split(";", 1)[0][:160] or "拓扑关系已确认"
    return value[:140]


def _compact_markdown(conclusion: AgentConclusion, score: RcaScore) -> str:
    chain = conclusion.causal_steps or [conclusion.root_cause_entity]
    nodes = [f"n{i}[\"{str(node).replace(chr(34), '')}\"]" for i, node in enumerate(chain)]
    edges = " --> ".join(f"n{i}" for i in range(len(chain)))
    graph = "flowchart LR\n    " + "\n    ".join(nodes)
    if len(chain) > 1:
        graph += "\n    " + edges
    priority = {"trace": 0, "log": 1, "metric": 2, "alert": 3, "topology": 4, "event": 5}
    selected = sorted(conclusion.evidence, key=lambda item: priority.get(item.source, 9))[:3]
    evidence_lines = "\n".join(
        f"- **{item.source}**：{_short_value(item)}" for item in selected
    ) or "- 未提供有效证据"
    gap = "证据链完整。" if score.evidence_recall >= 1 and score.evidence_precision >= 1 else (
        f"证据链仍有缺口：命中 {score.matched_checkpoints}/{score.total_checkpoints} 个 checkpoint，建议 Agent 优先补充缺失观测。"
    )
    return f"""# SRE Agent RCA 摘要

## 一眼结论

**{conclusion.root_cause_entity} 的 `{conclusion.fault_type}` 导致告警。**

{conclusion.summary}

```mermaid
{graph}
```

## 评估

| 指标 | 结果 |
|---|---:|
| 总分 | **{score.total:.2f}/100** |
| 根因 / 故障类型 | {score.entity:.0%} / {score.fault:.0%} |
| 因果链 | {score.chain_coverage:.0%} |
| 证据 checkpoint | {score.matched_checkpoints}/{score.total_checkpoints} |

## 关键证据

{evidence_lines}

## 下一步

{gap}

详细工具轨迹、完整证据和机器可读结果见同名 `.json` 文件。
"""
