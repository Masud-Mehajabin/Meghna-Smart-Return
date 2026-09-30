from typing import Dict
from fastapi import WebSocket

class ProgressManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.job_progress: Dict[str, dict] = {}

    async def connect(self, job_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[job_id] = websocket
        if job_id in self.job_progress:
            await self.send_progress(job_id, self.job_progress[job_id])

    def disconnect(self, job_id: str):
        if job_id in self.active_connections:
            del self.active_connections[job_id]
        if job_id in self.job_progress:
            del self.job_progress[job_id]

    async def send_progress(self, job_id: str, data: dict):
        self.job_progress[job_id] = data
        if job_id in self.active_connections:
            await self.active_connections[job_id].send_json(data)

progress_manager = ProgressManager()
