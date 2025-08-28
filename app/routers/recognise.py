# Plik: app/routers/recognise.py (nowy plik)

from fastapi import APIRouter, Depends
from typing import List, Optional
from pydantic import BaseModel
from sqlmodel import Session, select

from ..db import get_session
from ..models import Tool, ToolLoan
from ..dependencies import require_role

router = APIRouter()

# --- Schemat Pydantic dla odpowiedzi ---
# Definiuje dokładną strukturę JSON, jaką otrzyma klient.
class UnreturnedLoanDetail(BaseModel):
    tool_id: int
    loan_id: int
    width: Optional[float]
    height: Optional[float]
    area: Optional[float]
    mass: Optional[float]  # Będzie to pole weight_value z bazy

# --- Endpoint API ---

@router.get(
    "/loans",
    response_model=List[UnreturnedLoanDetail],
    dependencies=[Depends(require_role("admin", "moderator"))]
)
def get_unreturned_loans_with_details(session: Session = Depends(get_session)):
    """
    Zwraca listę wszystkich niezwróconych narzędzi wraz z ich kluczowymi
    parametrami (wymiary, masa) do celów rozpoznawania.
    """
    # Tworzymy zapytanie, które łączy tabele ToolLoan i Tool,
    # a następnie filtruje tylko te wypożyczenia, które nie zostały zwrócone.
    statement = select(ToolLoan, Tool).join(Tool).where(ToolLoan.returned == False)
    
    results = session.exec(statement).all()
    
    # Przetwarzamy wyniki z bazy danych na format zdefiniowany w UnreturnedLoanDetail
    response_data = []
    for loan, tool in results:
        response_data.append(
            UnreturnedLoanDetail(
                tool_id=tool.id,
                loan_id=loan.id,
                width=tool.width,
                height=tool.height,
                area=tool.area,
                mass=tool.weight_value, # Mapujemy weight_value na pole mass
            )
        )
        
    return response_data
