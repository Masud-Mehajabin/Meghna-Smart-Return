from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse
import os
from app.routers import (
    import_routes,
    log_routes,
    websocket_routes,
    db_routes,
    finalize_routes,
    check_error_routes,
    process_routes,
    auth_routes,
)
from app.services.db_manager import db_manager
from contextlib import asynccontextmanager

import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        yield
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        try:
            db_manager.disconnect()
        except Exception:
            pass

app = FastAPI(
    title="CIB Data Integration & Validation System (CIB-DIVS)",
    description="Production-grade web system for CIB CSV Import, Validation, and Oracle DB Automation.",
    lifespan=lifespan
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(auth_routes.router)
app.include_router(db_routes.router)
app.include_router(finalize_routes.router)
app.include_router(import_routes.router)
app.include_router(log_routes.router)
app.include_router(websocket_routes.router)
app.include_router(check_error_routes.router)
app.include_router(process_routes.router)

@app.get("/")
async def get_dashboard(request: Request):
    response = templates.TemplateResponse(request=request, name="index.html")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response

@app.get("/check-error")
async def get_check_error_page(request: Request):
    return templates.TemplateResponse(request=request, name="check_error.html")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    favicon_path = os.path.join("app", "static", "images", "favicon.ico")
    return FileResponse(favicon_path, media_type="image/x-icon")

if __name__ == "__main__":
    import uvicorn
    try:
        uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
    except (KeyboardInterrupt, SystemExit):
        pass
