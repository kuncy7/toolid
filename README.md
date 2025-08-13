# ToolID (clean)
Lekki backend **FastAPI** do zarządzania narzędziami, wypożyczeniami i konfiguracją wagi (serial).
Zbudowany pod **RPi5 (RaspiOS)**, Pydantic v2, SQLModel oraz rozdzielone schematy request/response.

## Szybki start
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m scripts.seed_admin
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Swagger: `http://<host>:8000/docs`
