from fastapi import APIRouter, HTTPException, status
from typing import List
from app.schemas.finalize_schemas import (
    TableInfo,
    FinalizeCheckRequest,
    FinalizeCheckResponse,
    FinalizeProcessRequest,
    FinalizeProcessResponse,
)
from app.services.finalize_service import finalize_service

router = APIRouter(prefix="/api/finalize", tags=["Finalize Imported Data"])


@router.get("/tables", response_model=List[TableInfo])
async def get_finalize_tables():
    """Returns the list of 6 approved CIB database tables for post-processing."""
    tables = finalize_service.get_approved_tables()
    return [TableInfo(table_name=t["table_name"], display_name=t["display_name"]) for t in tables]


@router.post("/check", response_model=FinalizeCheckResponse)
async def check_table(req: FinalizeCheckRequest):
    """
    Checks database connection, table existence, total records, and existing processed data status.
    """
    status_code, total_recs, proc_recs, msg = finalize_service.check_table_status(req.table_name)
    
    if status_code == "error":
        raise HTTPException(status_code=400, detail=msg)

    return FinalizeCheckResponse(
        status=status_code,
        table_name=req.table_name,
        total_records=total_recs,
        processed_records=proc_recs,
        message=msg
    )


@router.post("/process", response_model=FinalizeProcessResponse)
async def process_table(req: FinalizeProcessRequest):
    """
    Executes sequential sl_no update FIRST, commits, then runs branch ID update procedure in Oracle.
    """
    res = finalize_service.process_finalize(req.table_name, confirm_overwrite=req.confirm_overwrite)
    
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message", "Finalization failed."))

    return FinalizeProcessResponse(
        status="success",
        table_name=res["table_name"],
        branch_updated=res["branch_updated"],
        branch_updated_count=res.get("branch_updated_count"),
        sl_generated=res["sl_generated"],
        total_records=res["total_records"],
        sl_min=res["sl_min"],
        sl_max=res["sl_max"],
        message=res["message"]
    )
