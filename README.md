# SRE Agent Lab

Dataset-backed SRE agent evaluation lab for safe, repeatable outage diagnosis.

## What it provides

- RCA100 case adapter with offline metrics, logs, traces, events and topology.
- Read-only HTTPS tool gateway for remote agents.
- Deterministic root-cause, fault-type, causal-chain and evidence scoring.
- Chaos Mesh scenario adapters for a protected k3s lab namespace.
- Per-run isolation, audit records and concurrent participant runs.

## Quick start

```bash
uv sync
uv run pytest
```

Run the local offline API:

```bash
uv run python -m sre_lab.serve \
  --case-root data/rca100 \
  --ground-truth-root data/rca100/answer_key
```

The RCA100 files are intentionally not included in this public repository. Place an authorized local copy under `data/rca100/` before running dataset-backed cases. Never commit answer keys, participant tokens, kubeconfig files, or model API keys.

## Remote agent contract

See [`docs/agent-protocol.md`](docs/agent-protocol.md) and [`examples/agent_client.py`](examples/agent_client.py). The platform provides the URL and token; an agent only calls the HTTPS API and never receives cluster credentials.

## Sources and attribution

- **RCA100**: case structure and ground-truth format are adapted from the [AIOps RCA100 benchmark](https://www.aiops.cn/gitlab/aiops-live-benchmark/agenticopseval). RCA100 data is licensed by its upstream project under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) and is not redistributed here.
- **Chaos Mesh**: Kubernetes fault injection is designed against the [Chaos Mesh](https://github.com/chaos-mesh/chaos-mesh) APIs and CRDs. Chaos Mesh is an external dependency under its own [Apache-2.0 license](https://github.com/chaos-mesh/chaos-mesh/blob/master/LICENSE).

This repository is **not a fork of Chaos Mesh** and does not contain Chaos Mesh source code. It contains only a Python adapter, scenario manifests and safety policy; install and operate Chaos Mesh separately in the dedicated lab cluster.

## Scope

ChaosBlade is not part of this project. Host-level chaos, automatic remediation, production access, and FDB simulation are out of scope for the first release.
