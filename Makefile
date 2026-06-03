.PHONY: dev db-up db-down migrate api worker web test lint

# Start all infrastructure (Postgres + Redis)
db-up:
	docker compose up postgres redis -d

db-down:
	docker compose down

# Run Alembic migrations
migrate:
	cd apps/api && alembic upgrade head

# Dev servers (run in separate terminals)
api:
	cd apps/api && uvicorn app.main:app --reload --port 8000

worker:
	cd apps/api && celery -A app.workers.celery_app worker --loglevel=info -Q extraction,notifications

beat:
	cd apps/api && celery -A app.workers.celery_app beat --loglevel=info

web:
	cd apps/web && npm run dev

# Tests
test:
	cd apps/api && pytest -q

test-cov:
	cd apps/api && pytest --cov=app --cov-report=term-missing -q

# Simulate a webhook call (requires API running on :8000)
test-webhook:
	curl -s -X POST http://localhost:8000/api/v1/webhooks/recall \
	  -H "Content-Type: application/json" \
	  -d '{"event":"bot.status_change","data":{"bot":{"id":"test-bot-id"},"status":{"code":"call_ended"}}}'

# Quick extraction smoke-test via REST (paste a transcript)
test-extract:
	@echo "POST a transcript to test extraction (set MEETING_ID first):"
	@echo "  curl -X POST http://localhost:8000/api/v1/meetings/\$$MEETING_ID/upload-audio -F file=@recording.mp3"

# Check integration settings
test-integrations:
	curl -s http://localhost:8000/api/v1/integrations/settings | python -m json.tool

# Trigger overdue nudge cron manually
nudge-now:
	cd apps/api && celery -A app.workers.celery_app call app.workers.tasks.send_overdue_nudges

# Test /done slash command locally
test-done:
	curl -s -X POST http://localhost:8000/api/v1/slack/commands \
	  -d "command=/done&text=$(ITEM_ID)&user_name=test&user_id=U123" | python -m json.tool

# View open commitments (manager view API)
open-items:
	curl -s http://localhost:8000/api/v1/action-items/open | python -m json.tool

# Start watching Google Calendar via Composio
calendar-watch:
	curl -s -X POST http://localhost:8000/api/v1/calendar/watch \
	  -H "Content-Type: application/json" \
	  -d '{"entity_id":"placeholder"}' | python -m json.tool

# List upcoming auto-join meetings
upcoming:
	curl -s http://localhost:8000/api/v1/calendar/upcoming | python -m json.tool

# Trigger the safety-net check manually
join-check:
	cd apps/api && celery -A app.workers.celery_app call app.workers.tasks.check_and_join_upcoming

# Expose local API to the internet for Recall.ai webhooks (requires ngrok authtoken)
# After running, copy the https URL into API_BASE_URL in your .env
tunnel:
	C:/Users/chara/.tools/ngrok/ngrok.exe start --config ngrok.yml api

# Lint
lint:
	cd apps/api && ruff check .
	cd apps/web && npm run lint

# Full stack via Docker Compose
up:
	docker compose up --build

down:
	docker compose down -v
