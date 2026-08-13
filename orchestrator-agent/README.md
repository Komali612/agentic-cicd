# orchestrator-agent

The **Orchestrator** (PRD §4.1). It traverses a single repo, a list, or an entire
git org; classifies each repository; routes it to the matching CI worker; and
maintains the exception list. It **never authors a pipeline itself** (FR-0.6).

```
input (repo / list / org)
   → classify   (heuristic; LLM-assisted when a model is configured)
   → route      (dotnet_core → netcore-ci · dotnet_framework → netlegacy-ci)
   → invoke     (AgentClient → worker /run)  → collect WorkerResult
   → exception list  (unclassifiable · no worker · worker failure)
   → OrchestrationReport
```

## API

`POST /run` accepting any of the three input shapes (FR-0.1):

```json
{"input": {"repo_url": "https://github.com/acme/widget"}}
{"input": {"repos": ["https://github.com/acme/a", "https://github.com/acme/b"]}}
{"input": {"org": "acme"}}
```

Returns an `OrchestrationReport` (`results` + `exceptions`).

## Configuration

| Var | Required | Purpose |
|-----|----------|---------|
| `WORKER_NETCORE_CI_URL` | no | NetCoreCI worker URL (default in-cluster service name) |
| `WORKER_NETLEGACY_CI_URL` | no | NetLegacyCI worker URL |
| `GITHUB_TOKEN` | for private repos | read the repo tree/files + list org repos |
| `AGENT_MODEL` + `ANTHROPIC_API_KEY` | no | enable LLM-assisted classification (heuristic fallback otherwise) |

## Where the code lives

- `src/agent/classify.py` — heuristic + optional LLM classification
- `src/agent/router.py` — TechStack → worker `AgentClient`
- `src/agent/orchestrator.py` — the traverse/route/collect loop + exception list
- `src/agent/github.py` — read-only GitHub REST helpers
