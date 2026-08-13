# Agentic CI/CD — Stage 1

Stage-1 implementation of the *Agentic CI/CD Pipeline Automation* PRD (v2.0): an
**Orchestrator** plus the two fully-specified CI worker agents (**NetCoreCI**,
**NetLegacyCI**), built on the `agent-core` framework. Happy-path, unit tests +
SonarQube, substitute tools, pull-request output.

## Architecture

```
                         ┌───────────────────────┐
   repo / list / org ──▶ │   orchestrator-agent   │   classify → route → exception list
                         └───────────┬───────────┘   (never authors a pipeline)
                 dotnet_core ──────or──────  dotnet_framework
                         │                       │
             ┌───────────▼──────────┐ ┌──────────▼───────────┐
             │   netcore-ci-agent   │ │  netlegacy-ci-agent  │
             └───────────┬──────────┘ └──────────┬───────────┘
                         │  both use ▼            │
                         │   ┌──────────────┐     │
                         └──▶│ ci-authoring │◀────┘   Discover→Generate→Validate→Deploy
                             └──────┬───────┘         (3-retry, check-existing, open PR)
                                    ▼
                            ┌──────────────┐
                            │ agent-contracts │  shared models + AgentClient (comms)
                            └──────────────┘
```

| Package | Role |
|---------|------|
| **agent-contracts** | shared pydantic models (`RepoRef`, `Classification`, `WorkerRequest/Result`, `ExceptionEntry`, `OrchestrationReport`) + `AgentClient` HTTP comms |
| **ci-authoring** | the deterministic Discover→Generate→Validate→Deploy engine, validation, VCS/PR, `StepConfig` — shared by both CI agents |
| **netcore-ci-agent** | .NET Core 6/7/8 discoverer + deterministic workflow template (Linux/.NET CLI) |
| **netlegacy-ci-agent** | .NET FX 4.8 discoverer + template (Windows/MSBuild, no Docker/Helm) |
| **orchestrator-agent** | classify (heuristic + optional LLM) → route → exception list |
| **samples/** | a .NET Core app and a .NET FX app with no CI, to run against |

Each agent is an `agent-core` HTTP service (health/readiness/metrics, env config,
Dockerfile, Helm chart). The CI workers use a **deterministic handler** (the loop
runs in code, not an LLM tool-loop); the LLM is used only for classification, with
a heuristic fallback, so the whole system runs with **no API key** for the demo.

## PRD coverage (Stage 1)

| Area | Implemented | Deferred (Stage 2/3) |
|------|-------------|----------------------|
| Orchestrator | FR-0.1 (repo/list/org), 0.2 (classify+route), 0.4/0.5 (exception list), 0.6 (never authors) | 0.3 (call CD after CI — CD pending) |
| NetCoreCI | FR-N.1 discover, N.2 check-existing (skip if compliant), N.3 configurable steps, N.4 triggers, N.5 runner, N.6 build tool, N.7 tests+Sonar, N.11 lint-validate + 3-retry, N.12 PR (never merge) | N.8 SAST/SCA/DAST, N.9 Dynatrace/Splunk, N.10 Docker/SBOM/scan/Nexus/Helm; N.2 repair-in-place & N.11 sandboxed test-agent run (see Known gaps) |
| NetLegacyCI | FR-L.1/L.4/L.5 (Windows/MSBuild), tests+Sonar, lint-validate+retry, PR | SAST/SCA/DAST, monitoring, MSI packaging, L.3 repair-in-place (see Known gaps) |
| Cross-cutting | CR-2 (configurable steps), CR-3 check-existing (skip if compliant), NFR-2 (no self-merge), NFR-3 (3-retry cap) | CR-1 critical-finding gates (need Fortify/Sonatype/Wiz), CR-3 repair-in-place, NFR-1 async scale-out |
| Tooling | SonarQube (substitute for Fortify), unit tests | Fortify, Sonatype, Fortify WebInspect, Wiz, Nexus |

**Not started (pending customer input, per PRD §7/§9):** the 2 COBOL CI agents and
all 4 CD agents.

## Known gaps / simplifications (Stage 1)

Called out explicitly so nothing reads as more complete than it is. These are
deliberate Stage-1 scope decisions, not defects:

- **Validate is offline only.** `validate_workflow` parses the YAML and checks the
  required steps are present; it does **not** execute the workflow. FR-N.11 / FR-L.8
  also call for a *GitHub Actions test-agent run* (sandboxed execution) — that is
  Stage-2 (needs runners + a safe sandbox).
- **Existing pipelines are not repaired in place.** The engine checks for an existing
  workflow and, if it already contains the required steps, does nothing (`NO_CHANGE`).
  If it is deficient, the engine **regenerates** a fresh workflow rather than editing
  the existing one — FR-N.2 / FR-L.3 / CR-3's "repair/extend in place" is Stage-2.
  (The demo repos have no existing pipeline, so this path isn't exercised.)
- **The exception list is per-run, not persisted.** `OrchestrationReport` is returned
  in the HTTP response; FR-0.4's durable, reviewable list (for a nightly batch) is
  Stage-3.
- **Orchestration is synchronous/serial.** One blocking worker call per repo. The
  services are stateless and horizontally scalable, but NFR-1's 1,400–1,600-repo
  throughput needs concurrency / a queue — Stage-2/3.
- **.NET Framework build steps are approximations.** The generated .NET FX pipeline
  uses `dotnet test` and `dotnet-sonarscanner`; a production .NET FX pipeline more
  typically uses VSTest and the MSBuild SonarScanner. Refined in Stage-2.

## Run the local demo (no network, no token)

Each worker's Discover→Generate→Validate against its sample repo:

```bash
python -m venv .venv && . .venv/bin/activate
pip install ./agent-contracts ./ci-authoring ./netcore-ci-agent
python scripts/demo.py samples/sample-netcore-app      # prints the generated .NET Core workflow
```

(Repeat in a fresh venv with `netlegacy-ci-agent` against `sample-netlegacy-app`.)

## Run the tests

Libraries share one env; each agent needs its own (they all use the package name
`agent`):

```bash
pip install ./agent-contracts ./ci-authoring pytest && pytest agent-contracts ci-authoring
# then, per agent, in its own venv:
pip install ./agent-contracts ./ci-authoring ./netcore-ci-agent pytest && pytest netcore-ci-agent
```

## Deploy (Kubernetes)

Each agent ships its own image + Helm chart. Give each worker a `GITHUB_TOKEN`
secret; give the orchestrator the worker URLs and (optionally) an
`ANTHROPIC_API_KEY` for LLM-assisted classification.

```bash
make image && make deploy     # in each agent directory
```

> **Publishing note:** the agents install `agent-core` from its git tag, and
> `agent-contracts` / `ci-authoring` by name. For image builds and CI those two
> libraries must be published (git tag or a package index), exactly as `agent-core`
> already is. Local dev/test installs them from this working tree.

## Key design decisions

- **Deterministic templates.** Pipeline YAML comes from per-stack templates, so it
  is byte-identical every run — auditable across ~1,400 repos. The LLM never writes
  the YAML.
- **Deterministic gate + bounded retry in code.** The 3-attempt cap and the
  check-existing (skip-if-compliant) behaviour live in `ci-authoring/engine.py`,
  never delegated to the model.
- **Explicit contracts between agents.** The orchestrator and workers exchange only
  `agent-contracts` models; neither re-derives the other's decisions.
- **One shared engine.** Adding a new stack (e.g. COBOL, once scoped) means a new
  `Discoverer` + `WorkflowGenerator` — the loop, validation, retry, and PR handling
  are inherited.
