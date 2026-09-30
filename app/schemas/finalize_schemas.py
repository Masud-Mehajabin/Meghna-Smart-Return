from pydantic import BaseModel
from typing import List, Optional

class TableInfo(BaseModel):
    table_name: str
    display_name: str

class FinalizeCheckRequest(BaseModel):
    table_name: str

class FinalizeCheckResponse(BaseModel):
    status: str  # "ready", "existing_data", "no_data", "error"
    table_name: str
    total_records: int = 0
    processed_records: int = 0
    message: str

class FinalizeProcessRequest(BaseModel):
    table_name: str
    confirm_overwrite: bool = False

class FinalizeProcessResponse(BaseModel):
    status: str  # "success", "error"
    table_name: str
    branch_updated: bool = False
    branch_updated_count: Optional[int] = None
    sl_generated: bool = False
    total_records: int = 0
    sl_min: Optional[int] = None
    sl_max: Optional[int] = None
    message: str
