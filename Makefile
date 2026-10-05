.PHONY: dev test test-live lint seed demo docker docker-aws-local tf-validate deploy secrets

dev:              ## backend + frontend locally
	./scripts/dev.sh

test:             ## offline tests (backend, frontend, terraform validate)
	./scripts/test.sh

test-live:        ## also run live tests against real APIs (needs OPENROUTER_API_KEY)
	./scripts/test.sh --live

lint:
	./scripts/lint.sh

seed:             ## demo account with recorded real runs
	./scripts/seed_demo.sh

demo:             ## frontend-only demo mode (no backend, no keys)
	cd frontend && VITE_DEMO_MODE=true npx vite

docker:
	docker compose up --build

docker-aws-local: ## AWS code paths against LocalStack (no real AWS)
	docker compose --profile aws-local up --build

tf-validate:
	terraform -chdir=terraform fmt -check -recursive
	terraform -chdir=terraform/environments/dev init -backend=false && terraform -chdir=terraform/environments/dev validate

secrets:          ## REAL AWS: upload .env keys to Secrets Manager
	./scripts/set_secrets.sh

deploy:           ## REAL AWS: full deploy
	./scripts/deploy.sh
