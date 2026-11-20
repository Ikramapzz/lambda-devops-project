.PHONY: help install lint test build deploy-dev deploy-prod smoke-dev logs-dev local delete-dev delete-prod

help:
	@echo "make install       - create venv and install dev deps"
	@echo "make lint          - ruff + cfn-lint"
	@echo "make test          - unit tests"
	@echo "make build         - sam build"
	@echo "make deploy-dev    - build + deploy dev stack"
	@echo "make deploy-prod   - build + deploy prod stack (canary)"
	@echo "make smoke-dev     - run smoke tests against dev"
	@echo "make logs-dev      - tail Lambda logs for dev"
	@echo "make local         - run API locally (needs Docker)"
	@echo "make delete-dev    - delete dev stack"

install:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -r requirements-dev.txt

lint:
	ruff check src tests
	cfn-lint template.yaml

test:
	pytest -v

build:
	sam build

deploy-dev: build
	sam deploy --config-env dev

deploy-prod: build
	sam deploy --config-env prod

smoke-dev:
	API_URL=$$(aws cloudformation describe-stacks --stack-name lambda-devops-dev \
	  --region ap-south-1 \
	  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text) \
	  python3 tests/integration/test_api.py

logs-dev:
	sam logs --stack-name lambda-devops-dev --region ap-south-1 --tail

local: build
	sam local start-api --env-vars scripts/local-env.json

delete-dev:
	sam delete --stack-name lambda-devops-dev --region ap-south-1 --no-prompts

delete-prod:
	sam delete --stack-name lambda-devops-prod --region ap-south-1 --no-prompts
