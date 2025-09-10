# Plik: tests/test_api.py (cała zawartość)

from fastapi.testclient import TestClient
from app.main import app
from app.db import init_db, get_session
from app.models import User
from sqlmodel import Session, select
import pytest

# Klient testowy dla naszej aplikacji
client = TestClient(app)

# --- Przygotowanie środowiska testowego ---

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    # Inicjalizuj bazę danych przed uruchomieniem testów
    init_db()
    yield
    # Tutaj można by dodać logikę czyszczenia bazy po testach, jeśli to konieczne

# --- Testy ---

def test_health():
    """Testuje, czy endpoint /health działa poprawnie."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_unauthorized_access():
    """Testuje, czy próba dostępu do chronionego zasobu bez tokena zwraca błąd."""
    response = client.get("/api/users")
    # Oczekujemy błędu 401 (Unauthorized) lub 403 (Forbidden), zależy od implementacji
    assert response.status_code in [401, 403]

def test_admin_login_and_access():
    """
    Testuje proces logowania administratora i dostęp do chronionego zasobu.
    Ten test zakłada, że administrator z `seed_admin.py` istnieje.
    """
    # 1. Logowanie
    login_data = {
        "email": "admin@example.com",
        "password": "admin"
    }
    response = client.post("/api/auth/login", json=login_data)
    
    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data
    
    # 2. Dostęp do chronionego zasobu z tokenem
    access_token = token_data["access_token"]
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = client.get("/api/users", headers=headers)
    
    assert response.status_code == 200
    # Sprawdzamy, czy odpowiedź jest listą (oczekujemy listy użytkowników)
    assert isinstance(response.json(), list)
