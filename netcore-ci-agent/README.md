# netcore-ci-agent

The **NetCoreCI** worker agent — authors CI pipelines for **.NET Core 6/7/8**
applications targeting AKS (PRD §4.2). It is an `agent-core` HTTP service whose
handler runs the shared [`ci-authoring`](../ci-authoring) engine with a .NET
Core-specific discoverer and a deterministic workflow generator.

## What it does

Given a `WorkerRequest` (from the orchestrator), it runs:

```
clone → discover (.sln/.csproj, target framework, Linux runner)
      → generate  (build → unit tests → SonarQube)   ← deterministic template
      → validate  (YAML + required steps, offline)
      → deploy    (open a PR — never merges)
```

`build → test → sonar` is the Stage-1 step set (SonarQube substitutes for
Fortify). DAST, SBOM, image scan, Nexus, and Helm are Stage-2 and layer on via
the same `StepConfig` mechanism.

## API

`POST /run` with an agent-core envelope wrapping a serialized `WorkerRequest`:

```json
{"input": {"repo": {"url": "...", "owner": "acme", "name": "widget"},
           "classification": {"stack": "dotnet_core", "confidence": 1.0, "method": "heuristic"},
           "config": {}}}
```

Returns a `WorkerResult` (`pr_opened` | `no_change` | `exception`). Health at
`/healthz`, `/readyz`; metrics at `/metrics` (from agent-core).

## Configuration

| Var | Required | Purpose |
|-----|----------|---------|
| `AGENT_NAME` | no | display/label name |
| `GITHUB_TOKEN` | **yes** | token with `repo` scope to push a branch and open the PR |

This worker is **deterministic** — it needs no `AGENT_MODEL` / `ANTHROPIC_API_KEY`.

## Run locally

```bash
uv sync
cp .env.example .env          # set GITHUB_TOKEN
uv run agent                  # serves on http://localhost:8080
```

## Where the code lives

Only three files make this "the NetCoreCI agent"; the loop, validation, retry
bound, and PR handling are inherited from `ci-authoring`:

- `src/agent/discover.py` — `.sln`/`.csproj` + target-framework discovery
- `src/agent/generate.py` — the deterministic workflow template
- `src/agent/handler.py` — bridges agent-core's `/run` to the engine
