.PHONY: dev down logs test

# Start the full stack in the background.
dev:
	docker compose up -d --build

# Stop the stack (keeps data volumes).
down:
	docker compose down

# Tail API logs.
logs:
	docker compose logs -f api

# Run the pytest suite inside the running api container.
test:
	docker exec -e PYTHONPATH=/app construction_ai_api pytest /app/tests/ -v
