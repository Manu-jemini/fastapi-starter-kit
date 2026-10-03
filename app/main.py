from fastapi import FastAPI

from app.api.router import api_router
from app.api.routes import sessions
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.name, debug=settings.debug)
app.include_router(api_router, prefix=settings.api_v1_prefix)
app.include_router(sessions.router)
