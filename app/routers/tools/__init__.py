# Plik: app/routers/tools/__init__.py

from fastapi import APIRouter

from . import core, images, loans, weights

router = APIRouter()

router.include_router(core.router, tags=["Tools Core"])
router.include_router(images.router, tags=["Tools Images"])
router.include_router(loans.router, tags=["Tools Loans"])
router.include_router(weights.router, tags=["Tools Weights"])
