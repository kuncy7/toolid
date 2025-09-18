# Plik: app/main.py

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
import threading
import time
import serial
import re
import logging

from .config import settings
from .db import init_db, engine
from .routers import auth, users, tools, scale, integrations, warehouse, recognise
from .models import ScaleConfig, ScaleWeight
from .exceptions import register_exception_handlers  # <-- WAŻNY IMPORT

# Konfiguracja loggera
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def scale_listener(scale_config: ScaleConfig, stop_event: threading.Event):
    """
    Funkcja działająca w osobnym wątku, nasłuchująca na porcie szeregowym
    i zapisująca odczyty wagi do bazy danych.
    """
    while not stop_event.is_set():
        try:
            logging.info(
                f"Attempting to connect to scale {scale_config.id} on {scale_config.port}..."
            )
            ser = serial.Serial(
                port=scale_config.port,
                baudrate=scale_config.baudrate,
                parity=getattr(
                    serial, f"PARITY_{scale_config.parity.upper()}", serial.PARITY_NONE
                ),
                stopbits=getattr(
                    serial, f"STOPBITS_{scale_config.stop_bits}", serial.STOPBITS_ONE
                ),
                bytesize=getattr(serial, f"EIGHTBITS", serial.EIGHTBITS),
                timeout=scale_config.timeout / 1000.0,
            )
            logging.info(
                f"Successfully connected to scale {scale_config.id} on {scale_config.port}"
            )

            buffer = ""
            while not stop_event.is_set():
                data = ser.read(ser.in_waiting or 1).decode(errors="ignore")
                if data:
                    buffer += data
                    if "\n" in buffer:
                        lines = buffer.split("\n")
                        buffer = lines.pop()
                        for line in lines:
                            line = line.strip()
                            if not line:
                                continue

                            match = re.search(r"Net\s+([\d\.]+)\s+g", line)
                            if match:
                                try:
                                    weight_value = float(match.group(1))
                                    with Session(engine) as session:
                                        scale_weight = ScaleWeight(
                                            scale_id=scale_config.id,
                                            weight=weight_value,
                                        )
                                        session.add(scale_weight)
                                        session.commit()
                                        logging.info(
                                            f"Saved weight {weight_value}g for scale {scale_config.id}"
                                        )
                                except (ValueError, IndexError):
                                    logging.error(
                                        f"Could not parse weight from line: '{line}'"
                                    )

        except serial.SerialException as e:
            logging.error(
                f"Serial error with scale {scale_config.id} on {scale_config.port}: {e}"
            )
            stop_event.wait(5)  # Czekaj 5s lub do sygnału zatrzymania
        except Exception as e:
            logging.error(
                f"An unexpected error occurred with scale listener {scale_config.id}: {e}"
            )
            stop_event.wait(5)  # Czekaj 5s lub do sygnału zatrzymania


# --- NOWA LOGIKA CYKLU ŻYCIA APLIKACJI (LIFESPAN) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Kod, który uruchamia się przy starcie aplikacji
    logging.info("--- Running application startup logic ---")
    init_db()
    app.state.scale_threads = []

    if settings.SCALE_LISTENER_ENABLED:
        with Session(engine) as s:
            if not s.exec(select(ScaleConfig)).first():
                s.add(ScaleConfig())
                s.commit()
                logging.info("Created default scale configuration.")

            scales = s.exec(select(ScaleConfig)).all()
            logging.info(f"Found {len(scales)} scale(s) to monitor.")
            for scale_cfg in scales:
                stop_event = threading.Event()
                thread = threading.Thread(
                    target=scale_listener, args=(scale_cfg, stop_event), daemon=True
                )
                app.state.scale_threads.append(
                    {"thread": thread, "stop_event": stop_event, "id": scale_cfg.id}
                )
                thread.start()
                logging.info(
                    f"Started listener thread for scale {scale_cfg.id} on port {scale_cfg.port}"
                )
    else:
        logging.info("Scale listener is disabled by configuration.")

    yield  # W tym miejscu aplikacja jest gotowa i czeka na żądania

    # Kod, który uruchomi się przy zamykaniu aplikacji
    if settings.SCALE_LISTENER_ENABLED:
        logging.info("--- Running application shutdown logic ---")
        logging.info("Stopping all scale listener threads...")
        for item in app.state.scale_threads:
            item["stop_event"].set()

        for item in app.state.scale_threads:
            # Daj wątkowi 2 sekundy na zakończenie
            item["thread"].join(timeout=2)
            if item["thread"].is_alive():
                logging.warning(
                    f"Thread for scale {item['id']} did not terminate gracefully."
                )
        logging.info("All scale listener threads have been processed.")


app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan)

# --- REJESTRACJA HANDLERÓW WYJĄTKÓW ---
register_exception_handlers(app)  # <-- TO NAPRAWIA BŁĄD 500

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ALLOW_ORIGINS.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(tools.router, prefix="/api/tools", tags=["tools"])
app.include_router(scale.router, prefix="/api/scale", tags=["scale"])
app.include_router(
    integrations.router, prefix="/api/integrations", tags=["integrations"]
)
app.include_router(warehouse.router, prefix="/api/warehouse", tags=["warehouse"])
app.include_router(recognise.router, prefix="/api/recognise", tags=["recognise"])
