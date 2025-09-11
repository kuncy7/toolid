# Plik: app/exceptions.py (nowy plik)

from fastapi import Request, status
from fastapi.responses import JSONResponse

# --- Definicje własnych, semantycznych wyjątków ---

class ResourceNotFound(Exception):
    """Wyjątek rzucany, gdy zasób (np. użytkownik, narzędzie) nie został znaleziony."""
    def __init__(self, name: str, resource_id: any):
        self.name = name
        self.id = resource_id

class OperationForbidden(Exception):
    """Wyjątek rzucany, gdy operacja jest niedozwolona z powodów biznesowych."""
    def __init__(self, reason: str):
        self.reason = reason

# --- Funkcja rejestrująca "handlery" ---

def register_exception_handlers(app):
    """Rejestruje centralne handlery dla zdefiniowanych wyjątków."""

    @app.exception_handler(ResourceNotFound)
    async def resource_not_found_handler(request: Request, exc: ResourceNotFound):
        """Obsługuje błędy 404 w spójny sposób."""
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": f"{exc.name} with ID '{exc.id}' not found"},
        )

    @app.exception_handler(OperationForbidden)
    async def operation_forbidden_handler(request: Request, exc: OperationForbidden):
        """Obsługuje błędy 400 (Bad Request) w spójny sposób."""
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": exc.reason},
        )

