from pydantic import BaseModel
from typing import List, Optional

class ImportResult(BaseModel):
    total: int = 0
    processed: int = 0
    inserted: int = 0
    duplicates: int = 0
    failed: int = 0
    percentage: int = 0
    status: str = "waiting"

class ImportLogDetail(BaseModel):
    batch_id: str
    import_type: str
    source_file_name: str
    target_table: str
    started_at: str
    completed_at: str
    total_records: int
    inserted_records: int
    duplicate_records: int
    failed_records: int
    status: str
    failed_log_file: Optional[str]
