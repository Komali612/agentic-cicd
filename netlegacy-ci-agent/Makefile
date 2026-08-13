.PHONY: install run test image deploy

IMAGE ?= netlegacy-ci-agent
TAG ?= latest

install:
	uv sync

run:
	uv run agent

test:
	uv run pytest -q

image:
	docker build -t $(IMAGE):$(TAG) .

deploy:
	helm upgrade --install netlegacy-ci deploy/helm \
		--set image.repository=$(IMAGE) \
		--set image.tag=$(TAG)
