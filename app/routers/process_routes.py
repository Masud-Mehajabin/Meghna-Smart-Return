from fastapi import APIRouter, HTTPException, status, Response
from pydantic import BaseModel, Field
import oracledb
import logging
import datetime
from typing import Dict, Any, Optional
from app.services.db_manager import db_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Scheduler & Summary Process"])

MONTH_NAME_TO_NUM = {
    "january": "1",
    "february": "2",
    "march": "3",
    "april": "4",
    "may": "5",
    "june": "6",
    "july": "7",
    "august": "8",
    "september": "9",
    "october": "10",
    "november": "11",
    "december": "12",
}

MONTH_NUM_TO_NAME = {
    "1": "January", "2": "February", "3": "March", "4": "April",
    "5": "May", "6": "June", "7": "July", "8": "August",
    "9": "September", "10": "October", "11": "November", "12": "December"
}


class ProcessRunRequest(BaseModel):
    branch_id: Optional[str] = Field(default=None, description="Branch ID (optional, leave empty/null for All Branches)")
    month: str = Field(..., description="Selected month name or number (mandatory)")
    year: str = Field(..., description="Selected year e.g. 2026 (mandatory)")


class ReportDownloadRequest(BaseModel):
    pbranch_id: Optional[str] = Field(default=None, description="Branch ID (optional, leave empty/null for All Branches)")
    pmonth: str = Field(..., description="Selected month name or number (mandatory)")
    pyear: str = Field(..., description="Selected year e.g. 2026 (mandatory)")
    pschedule_nm: str = Field(..., description="Schedule Name e.g. elpaynt (mandatory)")


def get_current_error_count(conn) -> int:
    """
    Executes pkg_tfn_bbreturn.rsp_bbreturn_chk_error_code and returns total error count.
    """
    cursor = conn.cursor()
    out_cur = cursor.var(oracledb.CURSOR)
    cursor.callproc("pkg_tfn_bbreturn.rsp_bbreturn_chk_error_code", [out_cur])
    ref_cursor = out_cur.getvalue()
    if not ref_cursor or not ref_cursor.description:
        cursor.close()
        return 0
    rows = ref_cursor.fetchall()
    cursor.close()
    return len(rows)


def parse_process_inputs(branch_input: Optional[str], month_input: str, year_input: str):
    """
    Validates user-selected Branch ID, Month, and Year.
    """
    # 1. Branch ID (None/empty string implies All Branches)
    clean_branch = branch_input.strip() if branch_input and branch_input.strip() else None

    # 2. Month Validation
    clean_month = month_input.strip() if month_input else ""
    if not clean_month:
        raise HTTPException(
            status_code=400,
            detail="Month Required: Please select a month before continuing."
        )

    month_lower = clean_month.lower()
    if month_lower in MONTH_NAME_TO_NUM:
        num_str = MONTH_NAME_TO_NUM[month_lower]
        month_name = MONTH_NUM_TO_NAME[num_str]
    elif clean_month in MONTH_NUM_TO_NAME:
        num_str = clean_month
        month_name = MONTH_NUM_TO_NAME[num_str]
    elif clean_month.isdigit() and 1 <= int(clean_month) <= 12:
        num_str = str(int(clean_month))
        month_name = MONTH_NUM_TO_NAME[num_str]
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid Month Selection: Please select a valid month from the dropdown."
        )

    # 3. Year Validation
    clean_year = year_input.strip() if year_input and year_input.strip() else ""
    if not clean_year:
        raise HTTPException(
            status_code=400,
            detail="Year Required: Please enter or select a year before continuing."
        )
    if not clean_year.isdigit() or len(clean_year) != 4:
        raise HTTPException(
            status_code=400,
            detail="Invalid Year: Please enter a valid 4-digit year (e.g., 2026)."
        )

    return clean_branch, num_str, month_name, clean_year


@router.get("/process/error-status", response_model=Dict[str, Any])
async def get_error_status():
    """
    Checks current error count using pkg_tfn_bbreturn.rsp_bbreturn_chk_error_code.
    Returns error count and boolean flag indicating if Scheduler/Summary is allowed.
    """
    if not db_manager.is_connected():
        return {
            "success": False,
            "connected": False,
            "error_count": 0,
            "scheduler_summary_allowed": False,
            "detail": "Database Connection Required: Please connect to the Oracle database before checking status."
        }

    conn = db_manager.get_raw_connection()
    if not conn:
        return {
            "success": False,
            "connected": False,
            "error_count": 0,
            "scheduler_summary_allowed": False,
            "detail": "Database Connection Lost: Unable to acquire database session."
        }

    try:
        err_count = get_current_error_count(conn)
        conn.close()
        allowed = (err_count == 0)
        return {
            "success": True,
            "connected": True,
            "error_count": err_count,
            "scheduler_summary_allowed": allowed
        }
    except Exception as e:
        if conn:
            try: conn.close()
            except: pass
        logger.error(f"Error checking error status: {e}", exc_info=True)
        return {
            "success": False,
            "connected": True,
            "error_count": -1,
            "scheduler_summary_allowed": False,
            "detail": f"Failed to check CIB error status: {str(e)}"
        }

from app.services.audit_service import audit_service

REQUIRED_6_TABLES = ["a1_o1", "arv", "e2_p2", "c_form", "e3_p3", "bbreturn_manual_tm"]


@router.get("/workflow/status")
def get_workflow_status():
    """
    Returns real-time sequential workflow locking status for synchronizing Sidebar buttons & Dashboard cards.
    """
    if not db_manager.is_connected():
        return {
            "success": True,
            "connected": False,
            "all_6_completed": False,
            "completed_tables_count": 0,
            "completed_tables": [],
            "error_count": 0,
            "process_monitoring_completed": False,
            "unlocked": {
                "upload_validation": True,
                "error_summary": False,
                "process_monitoring": False,
                "download_reports": False
            }
        }

    conn = db_manager.get_raw_connection()
    if not conn:
        return {
            "success": True,
            "connected": False,
            "all_6_completed": False,
            "completed_tables_count": 0,
            "completed_tables": [],
            "error_count": 0,
            "process_monitoring_completed": False,
            "unlocked": {
                "upload_validation": True,
                "error_summary": False,
                "process_monitoring": False,
                "download_reports": False
            }
        }

    try:
        cursor = conn.cursor()

        # 1. Check completed CSV import batches from CSV_IMPORT_BATCH
        completed_tables = []
        try:
            cursor.execute("""
                SELECT DISTINCT LOWER(TARGET_TABLE) 
                FROM CSV_IMPORT_BATCH 
                WHERE UPPER(STATUS) = 'COMPLETED'
                  AND UPPER(IMPORT_TYPE) NOT IN ('SCHEDULER', 'SUMMARY', 'PROCESS_MONITORING')
                  AND COMPLETED_AT >= (SYSTIMESTAMP - INTERVAL '2' HOUR)
            """)
            rows = cursor.fetchall()
            for r in rows:
                if r and r[0] and r[0].lower() in REQUIRED_6_TABLES:
                    completed_tables.append(r[0].lower())
        except Exception as e:
            logger.warning(f"Error querying completed CSV import batches: {e}")

        completed_set = set(completed_tables)
        all_6_completed = (len(completed_set) >= 6)

        # 2. Check error count
        err_count = get_current_error_count(conn)

        # 3. Check if Process Monitoring (Scheduler or Summary) ran successfully
        pm_completed = False
        scheduler_completed = False
        summary_completed = False
        try:
            cursor.execute("""
                SELECT UPPER(IMPORT_TYPE), COUNT(*) 
                FROM CSV_IMPORT_BATCH
                WHERE UPPER(STATUS) = 'COMPLETED'
                  AND UPPER(IMPORT_TYPE) IN ('SCHEDULER', 'SUMMARY', 'PROCESS_MONITORING')
                GROUP BY UPPER(IMPORT_TYPE)
            """)
            rows = cursor.fetchall()
            for r in rows:
                if r and r[0]:
                    itype = r[0].upper()
                    cnt = r[1]
                    if cnt > 0:
                        pm_completed = True
                        if itype == 'SCHEDULER':
                            scheduler_completed = True
                        elif itype == 'SUMMARY':
                            summary_completed = True
        except Exception as e:
            logger.warning(f"Error querying process monitoring status: {e}")

        cursor.close()
        conn.close()

        # Sequential Logic Unlocks:
        step1_upload_val = True
        step2_error_summary = True
        step3_process_monitoring = (err_count == 0)
        step4_download_reports = True  # Always enabled per user directive

        return {
            "success": True,
            "connected": True,
            "all_6_completed": all_6_completed,
            "completed_tables_count": len(completed_tables),
            "completed_tables": completed_tables,
            "error_count": err_count,
            "process_monitoring_completed": pm_completed,
            "scheduler_completed": scheduler_completed,
            "summary_completed": summary_completed,
            "unlocked": {
                "upload_validation": step1_upload_val,
                "error_summary": step2_error_summary,
                "process_monitoring": step3_process_monitoring,
                "download_reports": step4_download_reports
            }
        }
    except Exception as e:
        if conn:
            try: conn.close()
            except: pass
        logger.error(f"Error checking workflow status: {e}", exc_info=True)
        return {
            "success": False,
            "connected": True,
            "all_6_completed": False,
            "completed_tables_count": 0,
            "completed_tables": [],
            "error_count": -1,
            "process_monitoring_completed": False,
            "unlocked": {
                "upload_validation": True,
                "error_summary": False,
                "process_monitoring": False,
                "download_reports": False
            }
        }


@router.post("/scheduler/run", response_model=Dict[str, Any])
def run_scheduler(req: ProcessRunRequest):
    """
    Executes pkg_tfn_bbreturn.fsp_bbreturen_schedule_master with user-selected Branch, Month, and Year.
    Offloaded to FastAPI thread pool to prevent blocking main asyncio loop.
    Strictly validates error_count == 0 prior to execution.
    Executes COMMIT on success, ROLLBACK on error.
    """
    if not db_manager.is_connected():
        raise HTTPException(
            status_code=400,
            detail="Database Connection Required: Please connect to the Oracle database before continuing."
        )

    branch_code, num_month, month_name, year_str = parse_process_inputs(req.branch_id, req.month, req.year)

    conn = db_manager.get_raw_connection()
    if not conn:
        raise HTTPException(
            status_code=503,
            detail="Database Connection Lost: Unable to acquire database session. Please reconnect and try again."
        )

    committed = False
    try:
        # Recheck error count
        err_count = get_current_error_count(conn)
        if err_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Operation Not Allowed: CIB error records currently exist (Total: {err_count}). Please resolve all errors before running Scheduler or Summary."
            )

        cursor = conn.cursor()
        branch_display = branch_code if branch_code else "All Branches"
        logger.info(f"Executing fsp_bbreturen_schedule_master with branch='{branch_code}', month='{num_month}', year='{year_str}'")
        
        cursor.callproc("pkg_tfn_bbreturn.fsp_bbreturen_schedule_master", [branch_code, num_month, year_str])
        cursor.close()

        # Commit database transaction
        conn.commit()
        committed = True

        try:
            b_id = audit_service.create_batch("Scheduler_Master", "SCHEDULER_EXEC", "SCHEDULER", "BBRETURN_SUMMARY")
            audit_service.update_batch(b_id, {"status": "COMPLETED", "total_records": 1, "inserted_records": 1})
        except Exception as ae:
            logger.warning(f"Scheduler audit logging warning: {ae}")

        logger.info("fsp_bbreturen_schedule_master executed and committed successfully.")
        return {
            "success": True,
            "title": "Scheduler Completed Successfully",
            "branch": branch_display,
            "month": month_name,
            "year": year_str,
            "detail": "The scheduler process has completed and changes have been committed successfully."
        }

    except HTTPException:
        raise
    except oracledb.Error as oe:
        logger.error(f"Oracle Scheduler Procedure Error: {oe}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Process Failed: The requested scheduler process could not be completed. Oracle error: {str(oe)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in run_scheduler: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Operation Failed: An unexpected error occurred while running scheduler. All uncommitted changes have been rolled back."
        )
    finally:
        if conn:
            if not committed:
                try:
                    conn.rollback()
                except: pass
            try:
                conn.close()
            except: pass


@router.post("/summary/run", response_model=Dict[str, Any])
def run_summary(req: ProcessRunRequest):
    """
    Executes pkg_tfn_bbreturn.fsp_bbreturen_summary_master with user-selected Branch, Month, and Year.
    Offloaded to FastAPI thread pool to prevent blocking main asyncio loop.
    Strictly validates error_count == 0 prior to execution.
    Executes COMMIT on success, ROLLBACK on error.
    """
    if not db_manager.is_connected():
        raise HTTPException(
            status_code=400,
            detail="Database Connection Required: Please connect to the Oracle database before continuing."
        )

    branch_code, num_month, month_name, year_str = parse_process_inputs(req.branch_id, req.month, req.year)

    conn = db_manager.get_raw_connection()
    if not conn:
        raise HTTPException(
            status_code=503,
            detail="Database Connection Lost: Unable to acquire database session. Please reconnect and try again."
        )

    committed = False
    try:
        # Recheck error count
        err_count = get_current_error_count(conn)
        if err_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Operation Not Allowed: CIB error records currently exist (Total: {err_count}). Please resolve all errors before running Scheduler or Summary."
            )

        cursor = conn.cursor()
        branch_display = branch_code if branch_code else "All Branches"
        logger.info(f"Executing fsp_bbreturen_summary_master with branch='{branch_code}', month='{num_month}', year='{year_str}'")
        
        cursor.callproc("pkg_tfn_bbreturn.fsp_bbreturen_summary_master", [branch_code, num_month, year_str])
        cursor.close()

        # Commit database transaction
        conn.commit()
        committed = True

        try:
            b_id = audit_service.create_batch("Summary_Master", "SUMMARY_EXEC", "SUMMARY", "BBRETURN_SUMMARY")
            audit_service.update_batch(b_id, {"status": "COMPLETED", "total_records": 1, "inserted_records": 1})
        except Exception as ae:
            logger.warning(f"Summary audit logging warning: {ae}")

        logger.info("fsp_bbreturen_summary_master executed and committed successfully.")
        return {
            "success": True,
            "title": "Summary Completed Successfully",
            "branch": branch_display,
            "month": month_name,
            "year": year_str,
            "detail": "The summary process has completed and changes have been committed successfully."
        }

    except HTTPException:
        raise
    except oracledb.Error as oe:
        logger.error(f"Oracle Summary Procedure Error: {oe}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Process Failed: The requested summary process could not be completed. Oracle error: {str(oe)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in run_summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Operation Failed: An unexpected error occurred while generating summary. All uncommitted changes have been rolled back."
        )
    finally:
        if conn:
            if not committed:
                try:
                    conn.rollback()
                except: pass
            try:
                conn.close()
            except: pass


class ReconciliationRequest(BaseModel):
    month: str = Field(..., description="Selected month name (mandatory)")
    year: str = Field(..., description="Selected year e.g. 2026 (mandatory)")


@router.post("/reconciliation/run", response_model=Dict[str, Any])
def run_reconciliation(req: ReconciliationRequest):
    """
    Executes pkg_tfn_bbreturn.rsp_bbret_schedule_crosscheck with user-selected Month and Year.
    Captures SYS_REFCURSOR OUT parameter presult and returns structured crosscheck items.
    Uses the existing Oracle database connection architecture — no separate connection system.
    """
    if not db_manager.is_connected():
        raise HTTPException(
            status_code=400,
            detail="Database Connection Required: Please connect to the Oracle database before continuing."
        )

    # Reuse existing month/year parser (branch_id=None → no branch filtering)
    _, num_month, month_name, year_str = parse_process_inputs(None, req.month, req.year)

    conn = db_manager.get_raw_connection()
    if not conn:
        raise HTTPException(
            status_code=503,
            detail="Database Connection Lost: Unable to acquire database session. Please reconnect and try again."
        )

    try:
        cursor = conn.cursor()

        # Bind presult as a SYS_REFCURSOR OUT parameter
        presult_var = cursor.var(oracledb.CURSOR)

        plsql = """
BEGIN
    pkg_tfn_bbreturn.rsp_bbret_schedule_crosscheck(
        pmonth  => :pmonth,
        pyear   => :pyear,
        presult => :presult
    );
END;
"""
        logger.info(
            f"Executing rsp_bbret_schedule_crosscheck with pmonth='{num_month}', pyear='{year_str}'"
        )

        cursor.execute(plsql, {
            "pmonth":  num_month,
            "pyear":   year_str,
            "presult": presult_var,
        })

        ref_cursor = presult_var.getvalue()
        results = []
        if ref_cursor:
            cols = [c[0].upper() for c in ref_cursor.description] if ref_cursor.description else []
            cursor_rows = ref_cursor.fetchall()
            for r in cursor_rows:
                row_dict = {}
                for col_name, val in zip(cols, r):
                    row_dict[col_name] = val
                results.append(row_dict)
            try:
                ref_cursor.close()
            except Exception:
                pass

        cursor.close()

        # Crosscheck is a validation/read procedure — no COMMIT required
        try:
            conn.close()
        except Exception:
            pass

        logger.info(f"rsp_bbret_schedule_crosscheck completed. Total items: {len(results)}")

        try:
            b_id = audit_service.create_batch("Reconciliation_Crosscheck", "RECONCILIATION_EXEC", "SCHEDULER", "BBRETURN_SUMMARY")
            audit_service.update_batch(b_id, {"status": "COMPLETED", "total_records": len(results), "inserted_records": len(results)})
        except Exception as ae:
            logger.warning(f"Reconciliation audit logging warning: {ae}")

        summary_msg = f"Cross-check complete. Analyzed {len(results)} report types for {month_name} {year_str}."
        if not results:
            summary_msg = f"No schedule archive or raw data records found for {month_name} {year_str}."

        return {
            "success": True,
            "title": "Reconciliation Completed",
            "month": month_name,
            "year": year_str,
            "total_records": len(results),
            "results": results,
            "presult": summary_msg
        }

    except HTTPException:
        raise
    except oracledb.Error as oe:
        logger.error(f"Oracle Reconciliation Procedure Error: {oe}", exc_info=True)
        error_msg = str(oe).strip()
        # Format friendly message for common Oracle error patterns
        clean_msg = error_msg
        if "ORA-06550" in error_msg or "PLS-00306" in error_msg:
            clean_msg = "Database Procedure Signature Mismatch: The procedure argument types or count do not match."
        elif "ORA-00942" in error_msg:
            clean_msg = "Database Table Missing: One of the required return tables or views does not exist."
        elif "ORA-01403" in error_msg:
            clean_msg = "No Data Found: The requested month serial code was not found in BBRET_MONTH."

        raise HTTPException(
            status_code=500,
            detail=f"Reconciliation Procedure Error: {clean_msg}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in run_reconciliation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Reconciliation Failed: An unexpected application error occurred while executing the crosscheck procedure."
        )
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


class ReconciliationDetailsRequest(BaseModel):
    month: str = Field(..., description="Selected month name e.g. September (mandatory)")
    year: str = Field(..., description="Selected year e.g. 2026 (mandatory)")
    report_type: str = Field(..., description="Report type e.g. E3P3, A1-O1 (mandatory)")


@router.post("/reconciliation/details", response_model=Dict[str, Any])
def run_reconciliation_details(req: ReconciliationDetailsRequest):
    """
    Executes pkg_tfn_bbreturn.rsp_bbret_schedule_crosscheck_details with user-selected Month, Year and Report Type.
    Captures SYS_REFCURSOR OUT parameter presult and returns mismatch reference details.
    """
    if not db_manager.is_connected():
        raise HTTPException(
            status_code=400,
            detail="Database Connection Required: Please connect to the Oracle database before continuing."
        )

    _, num_month, month_name, year_str = parse_process_inputs(None, req.month, req.year)
    rep_type = req.report_type.strip()

    conn = db_manager.get_raw_connection()
    if not conn:
        raise HTTPException(
            status_code=503,
            detail="Database Connection Lost: Unable to acquire database session. Please reconnect and try again."
        )

    try:
        cursor = conn.cursor()

        presult_var = cursor.var(oracledb.CURSOR)

        plsql = """
BEGIN
    pkg_tfn_bbreturn.rsp_bbret_schedule_crosscheck_details(
        pmonth       => :pmonth,
        pyear        => :pyear,
        preport_type => :preport_type,
        presult      => :presult
    );
END;
"""
        logger.info(
            f"Executing rsp_bbret_schedule_crosscheck_details with pmonth='{num_month}', pyear='{year_str}', preport_type='{rep_type}'"
        )

        cursor.execute(plsql, {
            "pmonth":       num_month,
            "pyear":        year_str,
            "preport_type": rep_type,
            "presult":      presult_var,
        })

        ref_cursor = presult_var.getvalue()
        results = []
        if ref_cursor:
            cols = [c[0].upper() for c in ref_cursor.description] if ref_cursor.description else []
            cursor_rows = ref_cursor.fetchall()
            for r in cursor_rows:
                row_dict = {}
                for col_name, val in zip(cols, r):
                    row_dict[col_name] = val
                results.append(row_dict)
            try:
                ref_cursor.close()
            except Exception:
                pass

        cursor.close()

        try:
            conn.close()
        except Exception:
            pass

        logger.info(f"rsp_bbret_schedule_crosscheck_details completed. Total items: {len(results)}")

        summary_msg = f"Found {len(results)} mismatch reference records for {rep_type} ({month_name} {year_str})."
        if not results:
            summary_msg = f"No mismatch reference records found for {rep_type} ({month_name} {year_str})."

        return {
            "success": True,
            "title": f"Mismatch Details: {rep_type}",
            "month": month_name,
            "year": year_str,
            "report_type": rep_type,
            "total_records": len(results),
            "results": results,
            "presult": summary_msg
        }

    except HTTPException:
        raise
    except oracledb.Error as oe:
        logger.error(f"Oracle Reconciliation Details Error: {oe}", exc_info=True)
        error_msg = str(oe).strip()
        clean_msg = error_msg
        if "ORA-06550" in error_msg or "PLS-00306" in error_msg:
            clean_msg = "Database Procedure Signature Mismatch: The procedure argument types or count do not match."
        elif "ORA-00942" in error_msg:
            clean_msg = "Database Table Missing: One of the required return tables or views does not exist."

        raise HTTPException(
            status_code=500,
            detail=f"Reconciliation Details Error: {clean_msg}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in run_reconciliation_details: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Reconciliation Details Failed: An unexpected error occurred while fetching mismatch details."
        )
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass



@router.post("/schedule-report/download")
def download_schedule_report(req: ReportDownloadRequest):
    """
    Executes pkg_tfn_bbreturn.rsp_bbreturn_schedule with pbranch_id, pmonth, pyear, pschedule_nm.
    Returns result formatted as pipe-separated (|) .txt file download.
    Preserves raw database string values including leading zeros (01, 0000) without scientific notation.
    """
    if not db_manager.is_connected():
        raise HTTPException(
            status_code=400,
            detail="Database Connection Required: Please connect to the Oracle database before continuing."
        )

    clean_sched = req.pschedule_nm.strip() if req.pschedule_nm else ""
    if not clean_sched:
        raise HTTPException(
            status_code=400,
            detail="Schedule Name Required: Please select a schedule name before continuing."
        )

    branch_code, num_month, month_name, year_str = parse_process_inputs(req.pbranch_id, req.pmonth, req.pyear)

    conn = db_manager.get_raw_connection()
    if not conn:
        raise HTTPException(
            status_code=503,
            detail="Database Connection Lost: Unable to acquire database session. Please reconnect and try again."
        )

    try:
        # Re-verify error count
        err_count = get_current_error_count(conn)
        if err_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Operation Not Allowed: CIB error records currently exist (Total: {err_count}). Please clear error log before downloading report."
            )

        cursor = conn.cursor()
        out_cur = cursor.var(oracledb.CURSOR)

        logger.info(f"Executing rsp_bbreturn_schedule with pbranch_id='{branch_code}', pmonth='{num_month}', pyear='{year_str}', pschedule_nm='{clean_sched}'")

        plsql = """
        BEGIN
            pkg_tfn_bbreturn.rsp_bbreturn_schedule(
                pbranch_id   => :pbranch_id,
                pmonth       => :pmonth,
                pyear        => :pyear,
                pschedule_nm => :pschedule_nm,
                presult      => :presult
            );
        END;
        """

        cursor.execute(plsql, {
            "pbranch_id": branch_code,
            "pmonth": num_month,
            "pyear": year_str,
            "pschedule_nm": clean_sched,
            "presult": out_cur
        })

        ref_cursor = out_cur.getvalue()
        rows = ref_cursor.fetchall() if ref_cursor else []
        cursor.close()
        conn.close()
        conn = None

        # Build pipe-separated text lines (preserving raw leading zeros and exact DB representation)
        lines = []
        for row in rows:
            if not row:
                continue
            # If the procedure returned pre-formatted string lines
            if len(row) == 1 and isinstance(row[0], str) and "|" in row[0]:
                line = row[0]
                if not line.endswith("|"):
                    line += "|"
                lines.append(line)
            else:
                formatted_cols = [str(val) if val is not None else "" for val in row]
                lines.append("|".join(formatted_cols) + "|")

        file_content = "\n".join(lines)
        if lines:
            file_content += "\n"

        filename = f"{clean_sched}_{year_str}_{num_month.zfill(2)}.txt"
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition"
        }

        return Response(
            content=file_content,
            media_type="text/plain",
            headers=headers
        )

    except HTTPException:
        raise
    except oracledb.Error as oe:
        logger.error(f"Oracle Schedule Report Procedure Error: {oe}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Process Failed: Unable to execute report procedure. Oracle error: {str(oe)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in download_schedule_report: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Operation Failed: An unexpected error occurred while generating report: {str(e)}"
        )
    finally:
        if conn:
            try: conn.close()
            except: pass


