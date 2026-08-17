# Secrets — managed with Doppler

Secrets are **never** stored in `.env` or committed to git. They live in
[Doppler](https://doppler.com) and are injected as environment variables at
launch (`doppler run -- …`). The agent code is unchanged — it still reads plain
env vars (`os.environ.get("GITHUB_TOKEN")`), so anything Doppler injects just
works.

## What is actually secret

The whole system has **two** secrets. Everything else in `.env` / Helm `env:`
(agent name, log level, worker URLs) is non-secret config and stays as-is.

| Secret | Used by | Required? |
|---|---|---|
| `GITHUB_TOKEN` | workers (push branch + open PR), orchestrator (read repos) | **Yes** to open a PR |
| `ANTHROPIC_API_KEY` | orchestrator, only when `AGENT_MODEL` is set (LLM-assisted classification) | No — optional |

Doppler layout we use:

```
project:  agentic-cicd
config:   dev   (also stg / prd for real environments)
secrets:  GITHUB_TOKEN, ANTHROPIC_API_KEY (optional)
```

All three agents share **one** project/config — they use the same token, so the
value is entered once. Each agent repo pins itself to it with a committed
`doppler.yaml` (project/config names only — no secret values).

---

## One-time setup (you must do this — I can't create your account or hold your token)

1. **Create a free Doppler account** at <https://doppler.com> (Developer plan is free).

2. **Log in the CLI** (opens a browser):

   ```bash
   doppler login
   ```

3. **Create the project** (this also creates the `dev` / `stg` / `prd` configs):

   ```bash
   doppler projects create agentic-cicd
   ```

4. **Add the secrets** to the `dev` config. You can import your existing GitHub
   token straight from the `gh` keychain — the value never gets typed or logged:

   ```bash
   doppler secrets set GITHUB_TOKEN="$(gh auth token)" \
     --project agentic-cicd --config dev
   # optional, only if you want LLM-assisted classification:
   # doppler secrets set ANTHROPIC_API_KEY="sk-ant-…" --project agentic-cicd --config dev
   ```

5. **Point each agent dir at the project** (reads the committed `doppler.yaml`):

   ```bash
   cd cicd/orchestrator-agent && doppler setup --no-interactive
   cd ../netcore-ci-agent     && doppler setup --no-interactive
   cd ../netlegacy-ci-agent   && doppler setup --no-interactive
   ```

---

## Run locally with Doppler

Wrap the normal launch command in `doppler run --`. Doppler injects the
secret(s); the non-secret overrides still come from each agent's `.env`.

```bash
# .NET Core worker
cd cicd/netcore-ci-agent
PYTHONPATH=src AGENT_NAME=netcore-ci AGENT_PORT=8081 doppler run -- python -m agent.main

# .NET Framework worker
cd cicd/netlegacy-ci-agent
PYTHONPATH=src AGENT_NAME=netlegacy-ci AGENT_PORT=8082 doppler run -- python -m agent.main

# Orchestrator (UI at http://localhost:8095)
cd cicd/orchestrator-agent
WORKER_NETCORE_CI_URL=http://localhost:8081 \
WORKER_NETLEGACY_CI_URL=http://localhost:8082 \
PYTHONPATH=src AGENT_NAME=orchestrator AGENT_PORT=8095 doppler run -- python -m agent.main
```

Check what Doppler will inject without running the app:

```bash
doppler secrets            # lists names (values masked)
doppler run -- env | grep -E 'GITHUB_TOKEN|ANTHROPIC_API_KEY'
```

---

## Kubernetes (Doppler Operator → native Secret)

The Helm chart already consumes a k8s Secret named `<agent>-secrets` via
`secretKeyRef` (see `deploy/helm/values.yaml` → `secretEnv`). The
[Doppler Kubernetes Operator](https://docs.doppler.com/docs/kubernetes-operator)
**creates and keeps that Secret in sync** from Doppler — so the Deployment needs
no change.

1. Install the operator:

   ```bash
   helm repo add doppler https://helm.doppler.com && helm repo update
   helm install doppler-operator doppler/doppler-kubernetes-operator \
     --namespace doppler-operator-system --create-namespace
   ```

2. Create a Doppler **service token** (read-only, scoped to `dev`) and store it
   as a k8s Secret the operator reads:

   ```bash
   TOKEN=$(doppler configs tokens create k8s-netcore --project agentic-cicd \
     --config dev --plain)
   kubectl create secret generic doppler-token-netcore \
     --from-literal=serviceToken="$TOKEN"
   ```

3. Apply a `DopplerSecret` that produces the `netcore-ci-secrets` Secret the
   chart already references (repeat per agent, changing the names):

   ```yaml
   apiVersion: secrets.doppler.com/v1alpha1
   kind: DopplerSecret
   metadata:
     name: netcore-ci-doppler
     namespace: default
   spec:
     tokenSecret:
       name: doppler-token-netcore     # k8s Secret holding the service token
     managedSecret:
       name: netcore-ci-secrets        # the Secret the Helm chart consumes
       namespace: default
   ```

   The managed Secret's keys are the Doppler secret **names** (`GITHUB_TOKEN`),
   which is why `values.yaml` references `key: GITHUB_TOKEN`.

4. Deploy as usual — the pod gets `GITHUB_TOKEN` from the synced Secret:

   ```bash
   make image && make deploy
   ```

---

## Why this is safer than `.env`

- No secret value is ever written to a file in the repo. `.env` (gitignored)
  now holds only non-secret overrides; `doppler.yaml` holds only project/config
  names.
- Doppler injects into the real process environment, so `os.environ.get(...)`
  sees the value — more reliable than `.env`, which pydantic only loaded for
  `AGENT_`-prefixed settings (raw `GITHUB_TOKEN` was never picked up from a file).
- Rotation is central: change the value once in Doppler; every agent (and the
  synced k8s Secret) gets it on next run/sync.
