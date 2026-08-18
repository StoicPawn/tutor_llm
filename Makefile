.PHONY: install run api models test check export-training
install:
	python -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt
models:
	ollama pull qwen3:4b
	ollama pull embeddinggemma
run:
	. .venv/bin/activate && streamlit run app.py
api:
	. .venv/bin/activate && uvicorn studyforge.api:app --host 0.0.0.0 --port 8000 --reload
check:
	. .venv/bin/activate && python -m compileall -q studyforge app.py tests
	. .venv/bin/activate && python -m unittest discover -s tests -v
export-training:
	. .venv/bin/activate && python training/export_dataset.py
test:
	. .venv/bin/activate && python -m unittest discover -s tests -v
