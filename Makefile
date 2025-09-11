.PHONY: venv install run seed test

venv:
	python3 -m venv .venv

install: venv
	# Instalujemy z pliku deweloperskiego, który zawiera też produkcyjne
	. .venv/bin/activate && pip install -U pip && pip install -r requirements-dev.txt

run:
	. .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000

seed:
	. .venv/bin/activate && python -m scripts.seed_admin

test:
	. .venv/bin/activate && pytest -q

format:
	. .venv/bin/activate && black .
