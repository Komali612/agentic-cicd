# netlegacy-ci-agent

The **NetLegacyCI** worker agent — authors CI pipelines for **.NET Framework 4.8**
applications targeting VM/IIS (PRD §4.3). It is an `agent-core` HTTP service whose
handler runs the shared [`ci-authoring`](../ci-authoring) engine with a .NET
Framework discoverer and a deterministic, **Windows-runner** workflow generator.

## What it does

```
clone → discover (.sln/.csproj, TargetFrameworkVersion, MSBuild/VS toolset, Windows runner)
      → generate  (NuGet restore → MSBuild → unit tests → SonarQube)   ← deterministic template
      → validate  (YAML + required steps, offline)
      → deploy    (open a PR — never merges)
```

The **generated** pipeline runs on `windows-latest`, builds with NuGet + MSBuild,
and produces an MSI/DLL — this stack has **no container image and no Helm chart**
(FR-L.7), so none is generated.

> Note: the *agent itself* is a normal containerized service (it has its own
> Dockerfile + Helm chart below). The "no container / no Helm" rule applies to the
> **pipelines it authors** for .NET FX apps, not to the agent's own deployment.

## API & configuration

Identical to the other CI workers: `POST /run` with a serialized `WorkerRequest`;
returns a `WorkerResult`. Requires `GITHUB_TOKEN` (`repo` scope). Deterministic —
no `AGENT_MODEL` / API key needed.

## Where the code lives

- `src/agent/discover.py` — .NET FX discovery (Windows, MSBuild/VS mapping)
- `src/agent/generate.py` — the deterministic Windows workflow template
- `src/agent/handler.py` — bridges agent-core's `/run` to the engine
