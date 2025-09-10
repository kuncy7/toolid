# Plik: app/main.py (zaktualizowana zawartość)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .config import settings
from .db import init_db, engine
from .routers import auth, users, tools, scale, integrations, warehouse, recognise
from sqlmodel import Session, select
from .models import ScaleConfig, ScaleWeight # <-- Dodano import ScaleWeight

# --- NOWA LOGIKA DLA WAG ---
import threading
import time
import serial
import re
import logging

# Konfiguracja loggera
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def scale_listener(scale_config: ScaleConfig):
    """
    Funkcja działająca w osobnym wątku, nasłuchująca na porcie szeregowym
    i zapisująca odczyty wagi do bazy danych.
    """
    while True:
        try:
            ser = serial.Serial(
                port=scale_config.port,
                baudrate=scale_config.baudrate,
                parity=getattr(serial, f'PARITY_{scale_config.parity.upper()}', serial.PARITY_NONE),
                stopbits=getattr(serial, f'STOPBITS_{scale_config.stop_bits}', serial.STOPBITS_ONE),
                bytesize=getattr(serial, f'EIGHTBITS', serial.EIGHTBITS),
                timeout=scale_config.timeout / 1000.0
            )
            logging.info(f"Successfully connected to scale {scale_config.id} on {scale_config.port}")
            
            buffer = ""
            while True:
                data = ser.read(ser.in_waiting or 1).decode(errors="ignore")
                if data:
                    buffer += data
                    if "\n" in buffer:
                        lines = buffer.split("\n")
                        buffer = lines.pop() # Ostatnia, potencjalnie niekompletna linia zostaje w buforze
                        for line in lines:
                            line = line.strip()
                            if not line: continue
                            
                            logging.info(f"Scale {scale_config.id} raw data: '{line}'")
                            # Szukamy linii z wagą netto, np. "Net 00594.0 g"
                            match = re.search(r"Net\s+([\d\.]+)\s+g", line)
                            if match:
                                try:
                                    weight_value = float(match.group(1))
                                    logging.info(f"Parsed weight from scale {scale_config.id}: {weight_value}g")
                                    
                                    # Zapis do bazy danych w nowej sesji
                                    with Session(engine) as session:
                                        scale_weight = ScaleWeight(scale_id=scale_config.id, weight=weight_value)
                                        session.add(scale_weight)
                                        session.commit()
                                        logging.info(f"Saved weight {weight_value}g for scale {scale_config.id}")
                                except (ValueError, IndexError) as e:
                                    logging.error(f"Could not parse weight from line: '{line}'. Error: {e}")

        except serial.SerialException as e:
            logging.error(f"Serial error with scale {scale_config.id} on {scale_config.port}: {e}")
            logging.info("Reconnecting in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            logging.error(f"An unexpected error occurred with scale listener {scale_config.id}: {e}")
            logging.info("Restarting listener in 5 seconds...")
            time.sleep(5)


app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ALLOW_ORIGINS.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()
    with Session(engine) as s:
        # Upewnij się, że istnieje domyślna konfiguracja wagi
        if not s.exec(select(ScaleConfig)).first():
            s.add(ScaleConfig())
            s.commit()
            logging.info("Created default scale configuration.")
        
        # Uruchomienie wątków nasłuchujących dla każdej wagi
        scales = s.exec(select(ScaleConfig)).all()
        logging.info(f"Found {len(scales)} scale(s) to monitor.")
        for scale in scales:
            thread = threading.Thread(target=scale_listener, args=(scale,), daemon=True)
            thread.start()
            logging.info(f"Started listener thread for scale {scale.id} on port {scale.port}")


@app.get("/health")
async def health():
    return {"status": "ok"}

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(tools.router, prefix="/api/tools", tags=["tools"])
app.include_router(scale.router, prefix="/api/scale", tags=["scale"])
app.include_router(integrations.router, prefix="/api/integrations", tags=["integrations"])
app.include_router(warehouse.router, prefix="/api/warehouse", tags=["warehouse"])
app.include_router(recognise.router, prefix="/api/recognise", tags=["recognise"])

