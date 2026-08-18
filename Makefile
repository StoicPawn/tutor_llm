.PHONY: install models run api local demo server-up server-down server-models server-token server-backup server-restore backup restore test check export-training

install:
	python -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt

models:
	ollama pull qwen3:4b
	ollama pull embeddinggemma

local: install models
	@echo "Local profile installed. Run: make run"

run:
	. .venv/bin/activate && DEPLOY_MODE=local streamlit run app.py

api:
	. .venv/bin/activate && DEPLOY_MODE=local uvicorn studyforge.api:app --host 127.0.0.1 --port 8000 --reload

demo:
	. .venv/bin/activate && python scripts/create_demo_workspace.py

server-token:
	@python -c "import secrets; print(secrets.token_urlsafe(48))"

server-up:
	cd deploy && mkdir -p backups && docker compose --env-file .env -f docker-compose.server.yml up -d --build

server-down:
	cd deploy && docker compose --env-file .env -f docker-compose.server.yml down

server-models:
	cd deploy && docker compose --env-file .env -f docker-compose.server.yml exec ollama ollama pull qwen3:4b
	cd deploy && docker compose --env-file .env -f docker-compose.server.yml exec ollama ollama pull embeddinggemma

server-backup:
	cd deploy && mkdir -p backups && docker compose --env-file .env -f docker-compose.server.yml exec tutor sh -lc 'python scripts/backup.py /backups/tutor-llm-backup-$$(date -u +%Y%m%dT%H%M%SZ).zip'

server-restore:
	@test -n "$(ARCHIVE)" || (echo "Usage: make server-restore ARCHIVE=backup-file.zip (file must be in deploy/backups/)" && exit 1)
	cd deploy && docker compose --env-file .env -f docker-compose.server.yml stop tutor
	cd deploy && docker compose --env-file .env -f docker-compose.server.yml run --rm --no-deps tutor python scripts/restore.py "/backups/$(notdir $(ARCHIVE))" --replace
	cd deploy && docker compose --env-file .env -f docker-compose.server.yml up -d tutor

backup:
	. .venv/bin/activate && python scripts/backup.py

restore:
	@test -n "$(ARCHIVE)" || (echo "Usage: make restore ARCHIVE=/path/backup.zip" && exit 1)
	. .venv/bin/activate && python scripts/restore.py "$(ARCHIVE)" --replace

check:
	. .venv/bin/activate && python -m compileall -q studyforge app.py tests scripts
	. .venv/bin/activate && python -m unittest discover -s tests -v

export-training:
	. .venv/bin/activate && python training/export_dataset.py

test:
	. .venv/bin/activate && python -m unittest discover -s tests -v
