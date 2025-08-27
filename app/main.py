from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .config import settings
from .db import init_db, engine
from .routers import auth, users, tools, scale, integrations, warehouse
from sqlmodel import Session, select
from .models import ScaleConfig

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
    # Ensure default ScaleConfig exists
    with Session(engine) as s:
        if not s.exec(select(ScaleConfig)).first():
            s.add(ScaleConfig())
            s.commit()

@app.get("/health")
async def health():
    return {"status": "ok"}

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(tools.router, prefix="/api/tools", tags=["tools"])
app.include_router(scale.router, prefix="/api/scale", tags=["scale"])
app.include_router(integrations.router, prefix="/api/integrations", tags=["integrations"])
app.include_router(warehouse.router, prefix="/api/warehouse", tags=["warehouse"])
