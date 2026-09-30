from fastapi import APIRouter, HTTPException, status
from app.schemas.db_schemas import DBConnectRequest, DBStatusResponse
from app.services.db_manager import db_manager

router = APIRouter(prefix="/api/db", tags=["Database Connection"])

@router.post("/connect", response_model=DBStatusResponse)
async def connect_db(req: DBConnectRequest):
    """
    Connect to Oracle Database with user provided runtime credentials.
    Validates host, port, service, username, password and tests with SELECT 1 FROM DUAL.
    """
    success, message = db_manager.connect(
        host=req.host,
        port=req.port,
        service=req.service,
        username=req.username,
        password=req.password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
        
    info = db_manager.get_status_info()
    return DBStatusResponse(
        connected=True,
        status_text="Connected",
        host=info.get("host"),
        port=info.get("port"),
        service=info.get("service"),
        username=info.get("username"),
        message=message
    )

@router.post("/disconnect", response_model=DBStatusResponse)
async def disconnect_db():
    """Disconnect current Oracle database session."""
    success, message = db_manager.disconnect()
    return DBStatusResponse(
        connected=False,
        status_text="Disconnected",
        message=message
    )

@router.get("/status", response_model=DBStatusResponse)
async def get_db_status():
    """Check current database status and parameters without password."""
    info = db_manager.get_status_info()
    return DBStatusResponse(
        connected=info["connected"],
        status_text=info["status_text"],
        host=info.get("host"),
        port=info.get("port"),
        service=info.get("service"),
        username=info.get("username"),
        message=info.get("message")
    )
