from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.progress_service import progress_manager

router = APIRouter()

@router.websocket("/ws/progress/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    await progress_manager.connect(job_id, websocket)
    try:
        while True:
            # Keep alive and wait
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        progress_manager.disconnect(job_id)
