.PHONY: install models run api local demo server-up server-down server-models test check export-training

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

server-up:
	cd deploy && docker compose -f docker-compose.server.yml up -d --build

server-down:
	cd deploy && docker compose -f docker-compose.server.yml down

server-models:
	cd deploy && docker compose -f docker-compose.server.yml exec ollama ollama pull qwen3:4b
	cd deploy && docker compose -f docker-compose.server.yml exec ollama ollama pull embeddinggemma

check:
	. .venv/bin/activate && python -m compileall -q studyforge app.py tests scripts
	. .venv/bin/activate && python -m unittest discover -s tests -v

export-training:
	. .venv/bin/activate && python training/export_dataset.py

test:
	. .venv/bin/activate && python -m unittest discover -s tests -v
