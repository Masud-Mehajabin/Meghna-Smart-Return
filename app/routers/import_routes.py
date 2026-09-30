from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
import os
import csv
from app.services.csv_import_service import csv_import_service
from app.services.mapping_config import get_mapping
from app.utils.file_utils import save_upload_file, get_safe_file_reader
from app.utils.hashing import generate_file_hash
from app.services.audit_service import audit_service
from app.services.db_manager import db_manager
from app.database import get_db_cursor

router = APIRouter()

@router.post("/import")
async def start_import(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    expected_filename: str = Form(...)
):
    # 1. Enforce Database Connection Access Control
    if not db_manager.is_connected():
        raise HTTPException(
            status_code=400,
            detail="Oracle Database is disconnected. Please click [DB Connection] in the navigation bar to connect to Oracle DB before importing data."
        )

    # 2. File Extension Validation
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Invalid file type. Only .csv files are permitted.")
    
    # 3. Flexible expected filename validation
    config = get_mapping(expected_filename)
    if not config:
        config = get_mapping(file.filename)

    if not config:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid import configuration mapping for '{file.filename}'."
        )

    # 4. Save uploaded file to temp path
    temp_path = save_upload_file(file, file.filename)

    # 5. Check file non-empty
    if os.path.getsize(temp_path) == 0:
        os.remove(temp_path)
        raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes).")

    # 6. Header Validation
    try:
        with get_safe_file_reader(temp_path) as f:
            reader = csv.DictReader(f)
            headers = list(reader.fieldnames or [])
            expected_cols = config.get("expected_columns", [])
            missing = [c for c in expected_cols if c not in headers]
            if missing:
                os.remove(temp_path)
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required CSV columns for table '{config['table']}': {', '.join(missing)}"
                )
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=400, detail=f"Failed to read CSV structure: {str(e)}")

    # 7. File Hash Generation
    file_hash = generate_file_hash(temp_path)

    # 8. Create Batch Audit Record (also triggers auto-purge of logs > 7 days)
    batch_id = audit_service.create_batch(file.filename, file_hash, "AUTO_IMPORT", config["table"])

    # 9. Trigger background processing
    background_tasks.add_task(csv_import_service.process_csv, temp_path, file.filename, batch_id)

    return {
        "status": "started",
        "job_id": batch_id,
        "message": "Import started...",
        "warning": None
    }
