# Plik: tests/test_api.py (cała, zaktualizowana zawartość)

from fastapi.testclient import TestClient
from app.main import app
from app.db import init_db, engine
from app.models import User
from app.security import hash_password
from sqlmodel import Session, select
import pytest
import uuid

# Klient testowy dla naszej aplikacji
client = TestClient(app)

# --- Przygotowanie środowiska testowego ---

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    """
    Inicjalizuje bazę danych i tworzy użytkownika admina PRZED uruchomieniem testów.
    Dzięki temu testy są niezależne od zewnętrznych skryptów.
    """
    init_db()
    with Session(engine) as session:
        # Sprawdź, czy użytkownik admin już istnieje
        admin_user = session.exec(
            select(User).where(User.email == "admin@example.com")
        ).first()
        
        # Jeśli nie istnieje, stwórz go
        if not admin_user:
            hashed_password = hash_password("admin")
            admin_user = User(
                id=str(uuid.uuid4()),
                first_name="Admin",
                last_name="Test",
                email="admin@example.com",
                password_hash=hashed_password,
                role="admin"
            )
            session.add(admin_user)
            session.commit()
    yield
    # Tutaj można by dodać logikę czyszczenia bazy po testach,
    # ale dla SQLite w CI nie jest to krytyczne.

# --- Testy ---

def test_health():
    """Testuje, czy endpoint /health działa poprawnie."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_unauthorized_access():
    """Testuje, czy próba dostępu do chronionego zasobu bez tokena zwraca błąd."""
    response = client.get("/api/users")
    assert response.status_code in [401, 403]

def test_admin_login_and_access():
    """
    Testuje proces logowania administratora i dostęp do chronionego zasobu.
    """
    # 1. Logowanie
    login_data = {
        "email": "admin@example.com",
        "password": "admin"
    }
    response = client.post("/api/auth/login", json=login_data)
    
    # Dodajmy czytelny komunikat błędu, jeśli logowanie się nie powiedzie
    assert response.status_code == 200, f"Login failed. Response: {response.json()}"
    
    token_data = response.json()
    assert "access_token" in token_data
    
    # 2. Dostęp do chronionego zasobu z tokenem
    access_token = token_data["access_token"]
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = client.get("/api/users", headers=headers)
    
    assert response.status_code == 200
    assert isinstance(response.json(), list)
