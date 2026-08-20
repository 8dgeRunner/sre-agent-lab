# Repository Instructions for Coding Agents

## First steps

1. Read `README.md` and the relevant document under `docs/`.
2. Run `uv sync` and `uv run pytest` before changing behavior.
3. Keep changes inside the requested module; do not add real credentials or dataset copies.

## Safety boundary

- Never read, expose, or commit RCA100 answer keys or participant tokens.
- Never request kubeconfig, model API keys, production access, or host access.
- Chaos Mesh changes must target the isolated `chaos-lab` namespace and remain reversible.
- Do not add automatic remediation or arbitrary shell execution.

## Verification

Run `uv run pytest` after changes. For scoring changes, add a focused test covering the affected ground-truth and evidence behavior.

The coding-agent instructions above are separate from the SRE participant workflow in `docs/agent-quickstart.md`.
