# NetCoreCI agent image. The agent clones and pushes target repositories, so git
# is installed in BOTH the build and runtime stages.
#
# NOTE: agent-contracts and ci-authoring must be resolvable at build time
# (published to your package index or git, like agent-core is). The local dev/test
# flow installs them from the working tree.
FROM python:3.11-slim AS build
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

FROM python:3.11-slim AS runtime
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
COPY --from=build /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=build /usr/local/bin /usr/local/bin
ENTRYPOINT ["agent"]
