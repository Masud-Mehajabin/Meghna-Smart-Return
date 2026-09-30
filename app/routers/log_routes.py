from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from app.database import get_db_cursor
import os
import re

from app.services.audit_service import audit_service

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
FAILED_LOGS_DIR = "logs/failed"


@router.get("/logs", response_class=HTMLResponse)
async def view_logs(request: Request):
    # Auto-purge logs older than 7 days
    try:
        audit_service.purge_logs_older_than_days(days=7)
    except Exception:
        pass

    logs = []
    with get_db_cursor() as cursor:
        if cursor:
            try:
                cursor.execute("""
                    SELECT BATCH_ID, SOURCE_FILE_NAME, TARGET_TABLE,
                           TOTAL_RECORDS, INSERTED_RECORDS, DUPLICATE_RECORDS,
                           FAILED_RECORDS, STATUS, STARTED_AT, COMPLETED_AT,
                           FAILED_LOG_FILE, FILE_HASH
                    FROM CSV_IMPORT_BATCH
                    ORDER BY STARTED_AT DESC
                """)
                for row in cursor.fetchall():
                    logs.append({
                        "batch_id":         row[0],
                        "source_file_name": row[1],
                        "target_table":     row[2],
                        "total_records":    row[3] or 0,
                        "inserted_records": row[4] or 0,
                        "duplicate_records":row[5] or 0,
                        "failed_records":   row[6] or 0,
                        "status":           row[7] or "COMPLETED",
                        "started_at":       str(row[8])[:19] if row[8] else None,
                        "completed_at":     str(row[9])[:19] if row[9] else None,
                        "failed_log_file":  row[10],
                        "file_hash":        row[11] or ""
                    })
            except Exception as e:
                pass  # Return empty list if audit tables don't exist yet
    return templates.TemplateResponse(request=request, name="logs.html", context={"logs": logs})


@router.get("/api/logs")
async def get_logs_api():
    """
    Returns import batch activity logs in JSON format.
    Automatically purges logs older than 7 days before returning results.
    """
    try:
        audit_service.purge_logs_older_than_days(days=7)
    except Exception:
        pass

    logs = []
    with get_db_cursor() as cursor:
        if cursor:
            try:
                cursor.execute("""
                    SELECT BATCH_ID, SOURCE_FILE_NAME, TARGET_TABLE,
                           TOTAL_RECORDS, INSERTED_RECORDS, DUPLICATE_RECORDS,
                           FAILED_RECORDS, STATUS, STARTED_AT, COMPLETED_AT,
                           FAILED_LOG_FILE, FILE_HASH
                    FROM CSV_IMPORT_BATCH
                    ORDER BY STARTED_AT DESC
                """)
                for row in cursor.fetchall():
                    logs.append({
                        "batch_id":         row[0],
                        "source_file_name": row[1],
                        "target_table":     row[2],
                        "total_records":    row[3] or 0,
                        "inserted_records": row[4] or 0,
                        "duplicate_records":row[5] or 0,
                        "failed_records":   row[6] or 0,
                        "status":           row[7] or "COMPLETED",
                        "started_at":       str(row[8])[:19] if row[8] else None,
                        "completed_at":     str(row[9])[:19] if row[9] else None,
                        "failed_log_file":  row[10],
                        "file_hash":        row[11] or ""
                    })
            except Exception:
                pass
    return {"logs": logs, "count": len(logs)}


@router.get("/logs/detail/{batch_id}")
async def get_log_detail(batch_id: str):
    """
    Returns full details of a specific batch import job, including failed records audit.
    """
    if not re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', batch_id, re.IGNORECASE):
        raise HTTPException(status_code=400, detail="Invalid batch ID format.")

    batch_info = None
    failed_details = []

    with get_db_cursor() as cursor:
        if not cursor:
            raise HTTPException(status_code=503, detail="Database connection unavailable.")

        cursor.execute("""
            SELECT BATCH_ID, SOURCE_FILE_NAME, TARGET_TABLE, FILE_HASH,
                   TOTAL_RECORDS, INSERTED_RECORDS, DUPLICATE_RECORDS,
                   FAILED_RECORDS, STATUS, STARTED_AT, COMPLETED_AT, FAILED_LOG_FILE
            FROM CSV_IMPORT_BATCH
            WHERE BATCH_ID = :1
        """, (batch_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Batch log not found.")

        batch_info = {
            "batch_id":         row[0],
            "source_file_name": row[1],
            "target_table":     row[2],
            "file_hash":        row[3],
            "total_records":    row[4],
            "inserted_records": row[5],
            "duplicate_records":row[6],
            "failed_records":   row[7],
            "status":           row[8],
            "started_at":       str(row[9]) if row[9] else None,
            "completed_at":     str(row[10]) if row[10] else None,
            "failed_log_file":  row[11],
        }

        # Fetch up to 100 failed records for details view
        try:
            cursor.execute("""
                SELECT SOURCE_ROW_NUMBER, STATUS, ERROR_MESSAGE, PROCESSED_AT
                FROM CSV_IMPORT_RECORD_AUDIT
                WHERE BATCH_ID = :1 AND STATUS = 'FAILED'
                ORDER BY SOURCE_ROW_NUMBER ASC
            """, (batch_id,))
            for f_row in cursor.fetchall():
                failed_details.append({
                    "row_number":    f_row[0],
                    "status":        f_row[1],
                    "error_message": f_row[2],
                    "processed_at":  str(f_row[3]) if f_row[3] else None
                })
        except Exception:
            pass

    return {
        "batch": batch_info,
        "failed_records": failed_details
    }


@router.delete("/logs/delete/{batch_id}")
async def delete_log(batch_id: str):
    """
    Delete a batch log entry and its associated failed CSV file.
    """
    if not re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', batch_id, re.IGNORECASE):
        raise HTTPException(status_code=400, detail="Invalid batch ID format.")

    failed_log_file = None

    with get_db_cursor() as cursor:
        if not cursor:
            raise HTTPException(status_code=503, detail="Database connection unavailable.")
        try:
            cursor.execute("SELECT FAILED_LOG_FILE FROM CSV_IMPORT_BATCH WHERE BATCH_ID = :1", (batch_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Log entry not found.")
            failed_log_file = row[0]

            cursor.execute("DELETE FROM CSV_IMPORT_RECORD_AUDIT WHERE BATCH_ID = :1", (batch_id,))
            cursor.execute("DELETE FROM CSV_IMPORT_BATCH WHERE BATCH_ID = :1", (batch_id,))
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database error: {e}")

    if failed_log_file:
        filepath = os.path.join(FAILED_LOGS_DIR, failed_log_file)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception:
                pass

    return JSONResponse({"status": "deleted", "batch_id": batch_id})


@router.get("/logs/download/{filename}")
async def download_failed_log(filename: str):
    # Security: prevent path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    filepath = os.path.join(FAILED_LOGS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found.")

    return FileResponse(path=filepath, filename=filename, media_type="text/csv")
