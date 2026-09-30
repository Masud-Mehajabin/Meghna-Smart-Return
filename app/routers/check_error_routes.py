from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
import oracledb
import logging
from typing import Dict, Any, List
from decimal import Decimal
import re
from app.services.db_manager import db_manager

from app.utils.data_transform import normalize_scientific_notation, format_2_decimal_string

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/check-error", tags=["Check Error"])

MONETARY_COLS = {
    "AMOUNT", "FC_AMOUNT", "FC_IN_USD", "AMOUNT_BDT", "BDT", "FOB_AMOUNT", "INVOICE_AMOUNT",
    "QUANTITY", "TOTAL_QUANTITY", "ARV_AMOUNT", "ARV_AMOUNT_USD", "ADJUSTED_AMOUNT",
    "ADJUSTED_AMOUNT_USD", "IMP_AMOUNT_PARTIAL", "IMP_AMOUNT_IMP_WISE", "FRIEGHT",
    "INSURANCE", "OTHER_CHARGES", "AMOUNT_CUSTOMS", "CMT_CUSTOMS", "TRIPLICATE_AMOUNT",
    "BANK_CHARGES", "RATE_BDT", "FCAMOUNT", "ROUND", "EFFECTED_REMITTANCE",
    "ISSUED_NOTES_COINS", "ISSUED_TC", "ISSUED_LC", "MOP_CASH", "MOP_TC",
    "MOP_CARD", "MOP_FDD", "MOP_MT", "MOP_OTHER", "MOP_OTHERS", "SFC_BANK", "SFC_FC_AC",
    "SFC_ERQ", "SFC_OTHER", "SFC_OTHERS", "AMOUNT_IN_BDT"
}


class UpdateErrorRequest(BaseModel):
    table_name: str = Field(..., description="Table name of selected error record")
    reference_no: str = Field(..., description="Reference number of selected error record")
    remarks: str = Field(..., description="Remarks/Error message of selected record")
    actual_reference: str = Field(..., description="User entered actual reference value")


@router.get("", response_model=Dict[str, Any])
async def get_check_errors():
    """
    Executes Oracle stored procedure `pkg_tfn_bbreturn.rsp_bbreturn_chk_error_code`,
    dynamically extracts all returned columns from the REF CURSOR description,
    and returns total count, column list, and row records formatted cleanly.
    """
    if not db_manager.is_connected():
        raise HTTPException(
            status_code=400,
            detail="Database Connection Required: Please connect to the Oracle database before checking errors."
        )

    conn = db_manager.get_raw_connection()
    if not conn:
        raise HTTPException(
            status_code=503,
            detail="Database Connection Lost: Unable to acquire database session. Please reconnect and try again."
        )

    try:
        cursor = conn.cursor()
        out_cur = cursor.var(oracledb.CURSOR)

        logger.info("Executing stored procedure: pkg_tfn_bbreturn.rsp_bbreturn_chk_error_code")
        cursor.callproc("pkg_tfn_bbreturn.rsp_bbreturn_chk_error_code", [out_cur])
        
        ref_cursor = out_cur.getvalue()
        if not ref_cursor or not ref_cursor.description:
            cursor.close()
            conn.close()
            return {
                "success": True,
                "total": 0,
                "columns": [],
                "rows": []
            }

        columns = [col[0] for col in ref_cursor.description]
        rows_raw = ref_cursor.fetchall()
        cursor.close()
        conn.close()

        rows_formatted: List[Dict[str, Any]] = []
        for r in rows_raw:
            row_dict = {}
            for idx, col_name in enumerate(columns):
                val = r[idx]
                c_upper = col_name.upper().strip()

                if val is None:
                    if c_upper in MONETARY_COLS:
                        row_dict[col_name] = "0.00"
                    else:
                        row_dict[col_name] = ""
                else:
                    val_str = str(val).strip()
                    if not val_str or val_str.lower() in ("none", "null"):
                        if c_upper in MONETARY_COLS:
                            row_dict[col_name] = "0.00"
                        else:
                            row_dict[col_name] = ""
                        continue

                    # 1. Normalize scientific notation if present
                    if re.search(r"[eE]", val_str):
                        is_monetary = c_upper in MONETARY_COLS
                        val_str = normalize_scientific_notation(val_str, is_identifier=not is_monetary) or val_str

                    # 2. Format numeric/monetary columns to exactly 2 decimal places
                    if c_upper in MONETARY_COLS:
                        val_str = format_2_decimal_string(val_str, default="0.00")
                    else:
                        if re.match(r"^-?\d+\.0+$", val_str):
                            val_str = val_str.split(".")[0]

                    row_dict[col_name] = val_str

            # 3. Format monetary/numeric & HS_CODE values dynamically based on column names or REFERENCE_COLUMN
            ref_col_val = str(row_dict.get("REFERENCE_COLUMN", "") or "").upper().strip()
            is_ref_hscode = "HS_CODE" in ref_col_val or "HSCODE" in ref_col_val
            is_ref_monetary = ref_col_val in MONETARY_COLS or any(m in ref_col_val for m in ("AMOUNT", "CHARGE", "QUANTITY", "RATE", "BDT", "USD", "CUSTOMS"))

            for col_k, val_v in list(row_dict.items()):
                if not val_v or not isinstance(val_v, str):
                    continue
                k_up = col_k.upper().strip()
                if "HS_CODE" in k_up or "HSCODE" in k_up:
                    if val_v.isdigit() and len(val_v) < 8:
                        row_dict[col_k] = val_v.zfill(8)
                elif is_ref_hscode and k_up in ("REFERENCE_NUMBER", "REFERENCE_NO", "REF_NO", "ACTUAL_REFERENCE"):
                    if val_v.isdigit() and len(val_v) < 8:
                        row_dict[col_k] = val_v.zfill(8)
                elif is_ref_monetary and k_up in ("ACTUAL_REFERENCE", "REFERENCE_NUMBER", "REFERENCE_NO", "REF_NO", "ACTUAL_VALUE", "VALUE", "ERROR_VALUE"):
                    row_dict[col_k] = format_2_decimal_string(val_v, default="0.00")
                elif k_up in MONETARY_COLS:
                    row_dict[col_k] = format_2_decimal_string(val_v, default="0.00")
                elif "REMARKS" in k_up or "MESSAGE" in k_up:
                    row_dict[col_k] = re.sub(
                        r'\b(HS_?CODE\s*[:=\-]?\s*)(\d{1,7})\b',
                        lambda m: m.group(1) + m.group(2).zfill(8),
                        val_v,
                        flags=re.IGNORECASE
                    )

            rows_formatted.append(row_dict)

        return {
            "success": True,
            "total": len(rows_formatted),
            "columns": columns,
            "rows": rows_formatted
        }

    except oracledb.Error as oe:
        if conn:
            try: conn.close()
            except: pass
        logger.error(f"Oracle Stored Procedure Error: {oe}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Oracle Procedure Execution Error: {str(oe)}"
        )
    except Exception as e:
        if conn:
            try: conn.close()
            except: pass
        logger.error(f"Unexpected error in get_check_errors: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Unable to Load Error Records: {str(e)}"
        )


@router.post("/update", response_model=Dict[str, Any])
async def update_error_record(req: UpdateErrorRequest):
    """
    Executes Oracle procedure `pkg_tfn_bbreturn.fsp_update_error_code`:
      p_table_name       => req.table_name
      p_rererence_no     => req.reference_no
      p_remarks          => req.remarks
      p_actual_reference => req.actual_reference
      p_output           => OUT parameter

    On success: COMMIT transaction.
    On failure: ROLLBACK transaction.
    """
    if not db_manager.is_connected():
        raise HTTPException(
            status_code=400,
            detail="Database Connection Required: Please connect to the Oracle database before updating the error record."
        )

    if not req.table_name or not req.table_name.strip():
        raise HTTPException(status_code=400, detail="Table Name Required: Invalid error record selected.")

    if not req.reference_no or not req.reference_no.strip():
        raise HTTPException(status_code=400, detail="Reference No Required: Invalid error record selected.")

    if not req.remarks or not req.remarks.strip():
        raise HTTPException(status_code=400, detail="Remarks Required: Invalid error record selected.")

    if not req.actual_reference or not req.actual_reference.strip():
        raise HTTPException(
            status_code=400,
            detail="Actual Reference Required: Please enter the Actual Reference before updating."
        )

    # Clean and format actual_reference (HS_CODE padding or 2-decimal place formatting for monetary fields)
    actual_ref_clean = req.actual_reference.strip()
    rem_up = req.remarks.upper()

    if actual_ref_clean.isdigit() and len(actual_ref_clean) < 8:
        # Check if reference_no or remarks indicates HS_CODE
        if "HS_CODE" in rem_up or "HSCODE" in rem_up or len(req.reference_no.strip()) == 8:
            actual_ref_clean = actual_ref_clean.zfill(8)
    elif any(m in rem_up for m in ("AMOUNT", "CHARGE", "QUANTITY", "RATE", "BDT", "USD", "CUSTOMS")) or any(m in req.reference_no.upper() for m in MONETARY_COLS):
        actual_ref_clean = format_2_decimal_string(actual_ref_clean, default=actual_ref_clean)

    conn = db_manager.get_raw_connection()
    if not conn:
        raise HTTPException(
            status_code=503,
            detail="Database Connection Lost: Unable to acquire database session. Please reconnect and try again."
        )

    try:
        cursor = conn.cursor()
        p_output = cursor.var(oracledb.STRING, size=4000)

        logger.info(
            f"Calling pkg_tfn_bbreturn.fsp_update_error_code for table={req.table_name}, "
            f"ref={req.reference_no}, remarks={req.remarks}, actual_ref={req.actual_reference}"
        )

        cursor.callproc(
            "pkg_tfn_bbreturn.fsp_update_error_code",
            [
                req.table_name.strip(),
                req.reference_no.strip(),
                req.remarks.strip(),
                actual_ref_clean,
                p_output
            ]
        )

        out_val = p_output.getvalue()
        cursor.close()

        logger.info(f"fsp_update_error_code returned p_output: {out_val}")

        is_error = False
        if out_val:
            val_lower = str(out_val).lower()
            if any(k in val_lower for k in ["error", "failed", "failure", "invalid", "exception", "no data"]):
                is_error = True

        if is_error:
            conn.rollback()
            conn.close()
            raise HTTPException(
                status_code=400,
                detail=f"Update Failed: {out_val or 'The error record could not be updated. No changes were committed.'}"
            )
        else:
            conn.commit()
            conn.close()
            return {
                "success": True,
                "message": "Update Completed Successfully. The error record has been updated. Please click Refresh Errors to view the latest error list.",
                "output": out_val or "Record updated successfully."
            }

    except oracledb.Error as oe:
        if conn:
            try:
                conn.rollback()
                conn.close()
            except: pass
        logger.error(f"Oracle Procedure Execution Error: {oe}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Update Failed: Database error while calling update procedure. ({str(oe)})"
        )
    except HTTPException:
        raise
    except Exception as e:
        if conn:
            try:
                conn.rollback()
                conn.close()
            except: pass
        logger.error(f"Unexpected error in update_error_record: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Update Failed: An unexpected error occurred. ({str(e)})"
        )
