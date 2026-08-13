# Orchestrator agent image. It talks to GitHub over HTTPS (no git subprocess), so
# git is only needed in the build stage (to install agent-core from its git repo).
#
# NOTE: agent-contracts must be resolvable at build time (index/git), like agent-core.
FROM python:3.11-slim AS build
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

FROM python:3.11-slim AS runtime
WORKDIR /app
COPY --from=build /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=build /usr/local/bin /usr/local/bin
ENTRYPOINT ["agent"]
