test:
	uv run pytest -v

lint:
	uv run ruff check .

fix:
	uv run ruff check . --fix

sync:
	uv sync

dev: 
	uv run uvicorn src.main:app --reload

start:
	uv run python -m src.main

ui:
	uv run streamlit run src/ui.py --server.port 8501
