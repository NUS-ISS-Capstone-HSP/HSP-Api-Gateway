.PHONY: install run run-local test gen-proto docker-up docker-down

install:
	python -m pip install -r requirements.txt

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8081 --reload

run-local:
	@if [ ! -f .env.local ]; then echo ".env.local not found"; exit 1; fi
	@set -a; . ./.env.local; set +a; uvicorn app.main:app --host "$${GATEWAY_HOST:-0.0.0.0}" --port "$${GATEWAY_PORT:-8081}" --reload

test:
	pytest -q

gen-proto:
	bash scripts/gen_proto.sh

docker-up:
	docker compose up --build

docker-down:
	docker compose down -v
