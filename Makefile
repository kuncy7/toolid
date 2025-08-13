.PHONY: venv install run seed test

venv:
	python3 -m venv .venv

install: venv
	. .venv/bin/activate && pip install -U pip && pip install -r requirements.txt

run:
	. .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000

seed:
	. .venv/bin/activate && python -m scripts.seed_admin

test:
	. .venv/bin/activate && pytest -q
