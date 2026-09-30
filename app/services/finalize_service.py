import logging
from typing import Dict, Any, List, Tuple
from app.services.db_manager import db_manager

logger = logging.getLogger(__name__)

# Strict backend configuration for approved CIB tables
FINALIZE_ALLOWED_TABLES: Dict[str, Dict[str, str]] = {
    "a1_o1": {
        "display_name": "A1_O1 (Triplicate List)",
        "table_capital": "A1_O1",
        "branch_column": "branch_id",
        "serial_column": "sl_no",
        "order_by": "exp_no"
    },
    "arv": {
        "display_name": "ARV (Online Reported ARV List)",
        "table_capital": "ARV",
        "branch_column": "branch_id",
        "serial_column": "sl_no",
        "order_by": "arv_id"
    },
    "e2_p2": {
        "display_name": "E2_P2 (e2-p2 RIT IMP Report)",
        "table_capital": "E2_P2",
        "branch_column": "branch_id",
        "serial_column": "sl_no",
        "order_by": "lc_id"
    },
    "c_form": {
        "display_name": "C_FORM (C Form Summary)",
        "table_capital": "C_FORM",
        "branch_column": "branch_id",
        "serial_column": "sl_no",
        "order_by": "cformid"
    },
    "e3_p3": {
        "display_name": "E3_P3 (Report TM Main For Bank HO)",
        "table_capital": "E3_P3",
        "branch_column": "branch_id",
        "serial_column": "sl_no",
        "order_by": "id_tmf"
    },
    "bbreturn_manual_tm": {
        "display_name": "BBRETURN_MANUAL_TM (Details TM Data)",
        "table_capital": "BBRETURN_MANUAL_TM",
        "branch_column": "branch_id",
        "serial_column": "sl_no",
        "order_by": "id_tmf"
    }
}


class FinalizeService:

    def get_approved_tables(self) -> List[Dict[str, str]]:
        return [
            {"table_name": k, "display_name": v["table_capital"]}
            for k, v in FINALIZE_ALLOWED_TABLES.items()
        ]

    def check_table_status(self, table_name: str) -> Tuple[str, int, int, str]:
        """
        Validates DB connection, table permission, table existence, and record counts.
        Returns: (status, total_records, processed_records, message)
        """
        table_key = table_name.lower()

        if not db_manager.is_connected():
            return "error", 0, 0, "Database Connection Required: Please connect to the Oracle database before finalizing imported data."

        if table_key not in FINALIZE_ALLOWED_TABLES:
            return "error", 0, 0, "Invalid Table Selection: Please select a valid approved CIB table."

        config = FINALIZE_ALLOWED_TABLES[table_key]
        capital_name = config["table_capital"]

        conn = db_manager.get_raw_connection()
        if not conn:
            return "error", 0, 0, "Database Connection Failed: Unable to acquire database session."

        try:
            cursor = conn.cursor()
            
            # 1. Total record count check
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_key}")
                row = cursor.fetchone()
                total_records = row[0] if row else 0
            except Exception as e:
                cursor.close()
                conn.close()
                logger.error(f"Error querying count for {table_key}: {e}")
                return "error", 0, 0, f"Table Error: Could not query table '{capital_name}'. Make sure the table exists."

            if total_records == 0:
                cursor.close()
                conn.close()
                return "no_data", 0, 0, f"No Data Found: The selected table '{capital_name}' does not contain any records to finalize."

            # 2. Existing processed data check (check if any sl_no or branch_id is non-null)
            try:
                cursor.execute(
                    f"SELECT COUNT(*) FROM {table_key} "
                    f"WHERE {config['serial_column']} IS NOT NULL OR {config['branch_column']} IS NOT NULL"
                )
                row_proc = cursor.fetchone()
                processed_records = row_proc[0] if row_proc else 0
            except Exception:
                processed_records = 0

            cursor.close()
            conn.close()

            if processed_records > 0:
                return (
                    "existing_data",
                    total_records,
                    processed_records,
                    f"Warning: Existing Data Detected in table '{capital_name}'. "
                    f"Found {processed_records} previously processed records."
                )

            return "ready", total_records, 0, "Table is ready for finalization."

        except Exception as e:
            if conn:
                try: conn.close()
                except: pass
            logger.error(f"Error checking status for table {table_key}: {e}")
            return "error", 0, 0, f"Unexpected error while checking table '{capital_name}'."

    def process_finalize(self, table_name: str, confirm_overwrite: bool = False) -> Dict[str, Any]:
        """
        Executes sequential sl_no update FIRST, COMMITS so PL/SQL procedure can read sl_no,
        then runs pkg_tfn_bbreturn.fsp_branch_name_update and COMMITS again.
        """
        table_key = table_name.lower()

        if not db_manager.is_connected():
            return {
                "status": "error",
                "table_name": table_name.upper(),
                "message": "Database Connection Required: Please connect to the database before continuing."
            }

        if table_key not in FINALIZE_ALLOWED_TABLES:
            return {
                "status": "error",
                "table_name": table_name.upper(),
                "message": "Invalid Table Selection: Please select a valid CIB table."
            }

        config = FINALIZE_ALLOWED_TABLES[table_key]
        capital_name = config["table_capital"]
        order_col = config["order_by"]
        serial_col = config["serial_column"]

        conn = db_manager.get_raw_connection()
        if not conn:
            return {
                "status": "error",
                "table_name": capital_name,
                "message": "Database Connection Failed: Session lost."
            }

        try:
            cursor = conn.cursor()

            # 1. Verify table has records
            cursor.execute(f"SELECT COUNT(*) FROM {table_key}")
            row = cursor.fetchone()
            total_records = row[0] if row else 0

            if total_records == 0:
                cursor.close()
                conn.close()
                return {
                    "status": "error",
                    "table_name": capital_name,
                    "message": f"No Data Found: The selected table '{capital_name}' does not contain any records to finalize."
                }

            # 2. STEP 1: Sequential SL_NO Population FIRST
            logger.info(f"Step 1: Populating {serial_col} sequentially FIRST for table: {table_key}")
            try:
                sql_sl = f"""
                UPDATE {table_key} t
                SET {serial_col} = (
                    SELECT rn
                    FROM (
                        SELECT ROWID AS rid,
                               ROW_NUMBER() OVER (ORDER BY {order_col}, ROWID) AS rn
                        FROM {table_key}
                    ) x
                    WHERE x.rid = t.ROWID
                )
                """
                cursor.execute(sql_sl)
                # CRITICAL: Commit sl_no updates immediately so the PL/SQL procedure sees the committed sl_no rows!
                conn.commit()
                logger.info(f"Successfully populated and committed {serial_col} sequentially for '{table_key}'.")
            except Exception as se:
                conn.rollback()
                cursor.close()
                conn.close()
                logger.error(f"Serial Number Update Failed for {table_key}: {se}")
                return {
                    "status": "error",
                    "table_name": capital_name,
                    "message": f"Serial Number Update Failed: The {serial_col} values could not be generated."
                }

            # 3. STEP 2: Execute Oracle Branch Update Function/Procedure
            # Try both uppercase (A1_O1) and lowercase (a1_o1) table name variants to ensure PL/SQL match
            logger.info(f"Step 2: Executing branch update procedure pkg_tfn_bbreturn.fsp_branch_name_update for table: {capital_name}")
            procedure_success = False
            proc_error_msg = ""

            plsql = """
            BEGIN
                pkg_tfn_bbreturn.fsp_branch_name_update(
                    p_table_name => :p_table_name
                );
            END;
            """

            # Try uppercase table name first (standard in Oracle PL/SQL)
            try:
                cursor.execute(plsql, p_table_name=capital_name)
                conn.commit()
                procedure_success = True
                logger.info(f"Executed pkg_tfn_bbreturn.fsp_branch_name_update with p_table_name='{capital_name}'")
            except Exception as pe1:
                logger.warning(f"Procedure execution with uppercase '{capital_name}' returned error: {pe1}. Trying lowercase '{table_key}'...")
                proc_error_msg = str(pe1)
                try:
                    conn.rollback()
                    cursor.execute(plsql, p_table_name=table_key)
                    conn.commit()
                    procedure_success = True
                    logger.info(f"Executed pkg_tfn_bbreturn.fsp_branch_name_update with p_table_name='{table_key}'")
                except Exception as pe2:
                    conn.rollback()
                    logger.error(f"Procedure execution failed for both upper and lower table names: {pe2}")
                    proc_error_msg = str(pe2)

            if not procedure_success:
                cursor.close()
                conn.close()
                return {
                    "status": "error",
                    "table_name": capital_name,
                    "message": f"Branch ID Update Failed: The branch information procedure could not be executed for '{capital_name}'. Details: {proc_error_msg}"
                }

            # 4. STEP 3: Verify results and check branch_id non-null count
            cursor.execute(f"SELECT MIN({serial_col}), MAX({serial_col}) FROM {table_key}")
            sl_row = cursor.fetchone()
            sl_min = sl_row[0] if sl_row and sl_row[0] is not None else 1
            sl_max = sl_row[1] if sl_row and sl_row[1] is not None else total_records

            # Check branch_id count
            cursor.execute(f"SELECT COUNT(*) FROM {table_key} WHERE branch_id IS NOT NULL")
            branch_row = cursor.fetchone()
            branch_updated_count = branch_row[0] if branch_row else 0
            logger.info(f"Branch ID check for '{capital_name}': {branch_updated_count} rows have non-null branch_id.")

            cursor.close()
            conn.close()

            logger.info(f"Finalization completed successfully for {capital_name}: {total_records} records processed ({branch_updated_count} branch IDs updated).")

            return {
                "status": "success",
                "table_name": capital_name,
                "branch_updated": True,
                "branch_updated_count": branch_updated_count,
                "sl_generated": True,
                "total_records": total_records,
                "sl_min": sl_min,
                "sl_max": sl_max,
                "message": "Finalization Completed Successfully"
            }

        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                    conn.close()
                except: pass
            logger.error(f"Unexpected error during finalization of {table_key}: {e}", exc_info=True)
            return {
                "status": "error",
                "table_name": capital_name,
                "message": f"Operation Failed: An unexpected error occurred while finalizing '{capital_name}'."
            }


finalize_service = FinalizeService()
