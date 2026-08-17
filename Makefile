.PHONY: install run models test export-training
install:
	python -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt
models:
	ollama pull qwen3:4b-instruct
	ollama pull embeddinggemma
run:
	. .venv/bin/activate && streamlit run app.py
export-training:
	. .venv/bin/activate && python training/export_dataset.py
test:
	. .venv/bin/activate && python -m unittest discover -s tests -v
