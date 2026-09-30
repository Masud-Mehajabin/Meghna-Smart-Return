import csv
import asyncio
import logging
from app.services.mapping_config import get_mapping
from app.services.progress_service import progress_manager
from app.utils.hashing import generate_record_hash
from app.utils.data_transform import (
    normalize_scientific_notation, strip_leading_zeros,
    parse_oracle_date, clean_numeric, clean_integer, clean_currency_code, is_numeric_decimal_string
)
from app.utils.file_utils import generate_failed_log, get_safe_file_reader
from app.database import get_connection
from app.config import settings

from app.services.finalize_service import finalize_service

logger = logging.getLogger(__name__)


class CSVImportService:

    async def process_csv(self, file_path: str, file_name: str, batch_id: str):
        config = get_mapping(file_name)
        if not config:
            await self._send(batch_id, status="failed",
                             msg="Unknown mapping configuration")
            return

        target_table     = config["table"]
        dup_key_cols     = config.get("duplicate_key_columns", [])
        sci_cols         = {c.lower().strip() for c in config.get("scientific_columns", [])}
        strip_zero_cols  = {c.lower().strip() for c in config.get("strip_leading_zero_columns", [])}
        date_cols        = {c.lower().strip() for c in config.get("date_columns", [])}
        qty_cols         = {c.lower().strip() for c in config.get("quantity_columns", [])}
        numeric_cols     = {c.lower().strip() for c in config.get("numeric_columns", [])}
        int_cols         = {c.lower().strip() for c in config.get("integer_columns", [])}
        currency_cols    = {c.lower().strip() for c in config.get("currency_code_columns", [])}
        col_mapping      = config.get("column_mapping", {})
        extra_sql_cols   = config.get("extra_sql_columns", {})
        expected_cols    = config.get("expected_columns", [])

        failed_rows = []
        total_rows = processed = inserted = duplicates = 0

        # ── 1. Count rows & validate headers ────────────────────────────
        try:
            with get_safe_file_reader(file_path) as f:
                reader = csv.DictReader(f)
                headers = list(reader.fieldnames or [])

                missing = [c for c in expected_cols if c not in headers]
                if missing:
                    await self._send(batch_id, status="failed",
                                     msg=f"Missing CSV columns: {missing}")
                    return
                total_rows = sum(1 for _ in reader)
        except Exception as e:
            await self._send(batch_id, status="failed",
                             msg=f"File read error: {e}")
            return

        await self._send(batch_id, total=total_rows, status="processing")

        # ── 2. Open one DB connection for the whole import ───────────────
        conn = get_connection()
        if not conn:
            await self._send(batch_id, total=total_rows, status="failed",
                             msg="Database is disconnected or unavailable. Please connect to Oracle Database.")
            return

        # ── 3. Check & Delete Existing Data from Target Table ──────────────
        # Flow: Upload CSV -> Check Existing Data -> Existing Data Found? -> YES: Delete & Commit -> Insert New CSV -> Commit
        try:
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM {target_table}")
            existing_count = cur.fetchone()[0] or 0
            if existing_count > 0:
                logger.info(f"Existing data found ({existing_count} records) in '{target_table}'. Deleting existing data...")
                cur.execute(f"DELETE FROM {target_table}")
                conn.commit()
                logger.info(f"Successfully deleted and committed removal of {existing_count} records from '{target_table}'.")

                # Clean up associated record audit entries for target_table
                try:
                    cur.execute("DELETE FROM CSV_IMPORT_RECORD_AUDIT WHERE UPPER(TARGET_TABLE) = UPPER(:1)", (target_table,))
                    conn.commit()
                except Exception as ae:
                    logger.warning(f"Audit cleanup warning for {target_table}: {ae}")
            else:
                logger.info(f"No existing data found in '{target_table}'.")
            cur.close()
        except Exception as e:
            logger.error(f"Error checking or deleting existing data in '{target_table}': {e}", exc_info=True)
            await self._send(batch_id, total_rows, status="failed",
                             msg=f"Error clearing existing data from table '{target_table}': {e}")
            if conn:
                try: conn.close()
                except: pass
            return

        # ── 4. Determine which CSV headers to map & build INSERT SQL ──────
        if col_mapping:
            data_keys = [h for h in headers if h in col_mapping]
            db_cols   = [col_mapping[h] for h in data_keys]
        else:
            data_keys = headers
            db_cols   = headers

        col_exprs = []
        bind_idx  = 1

        for db_col in db_cols:
            col_exprs.append((db_col, f":{bind_idx}"))
            bind_idx += 1

        for db_col, sql_expr in extra_sql_cols.items():
            col_exprs.append((db_col, sql_expr))

        cols_str   = ", ".join(c[0] for c in col_exprs)
        vals_str   = ", ".join(c[1] for c in col_exprs)
        insert_sql = f"INSERT INTO {target_table} ({cols_str}) VALUES ({vals_str})"
        logger.info(f"INSERT SQL: {insert_sql}")

        CODE_COLUMNS = {
            "currency code", "currency_code", "country code", "country_code",
            "unit code", "unit_code", "hscode", "hs_code", "category code", "category_code",
            "purpose code", "purpose_code", "purpose_code_sbb", "adscode", "exp no",
            "exp_no", "trp ad", "trp_ad", "lc id", "lc_id", "lc/ contract", "contract",
            "imp no", "imp_no", "id_tmf", "exp year", "exp_year", "imp serial", "imp_serial",
            "imp year", "imp_year", "cformid", "cform_id", "arv id", "arv_id", "unique_id",
            "bank_reference", "bank ref", "outward_ref", "inward_ref", "erc no", "erc no.",
            "irc no", "serial", "month_id", "company_type_id", "company_id", "instrument_id",
            "addressee_id", "ben_account", "applicant account number", "passport_no",
            "contact_no", "return id", "bank bill no", "invoice no", "commodity"
        }

        # ── 5. Process & Insert rows ──────────────────────────────────────
        batch_values: list = []
        batch_meta:   list = []

        try:
            with get_safe_file_reader(file_path) as f:
                reader = csv.DictReader(f)

                for row_num, row in enumerate(reader, start=2):
                    processed += 1

                    # --- Normalize all values ---
                    normalized = {}
                    for col in headers:
                        raw = row.get(col, "") or ""
                        col_lower = col.lower().strip()
                        is_id = (col_lower in CODE_COLUMNS) or (col_lower in sci_cols) or (col_lower in strip_zero_cols)

                        # Pre-normalize scientific notation or float integer strings across all columns & CSV files
                        if raw and ("E" in str(raw).upper() or "e" in str(raw) or ".0" in str(raw)):
                            raw = normalize_scientific_notation(raw, is_identifier=is_id)

                        if col_lower in currency_cols or col_lower in ("currency code", "currency_code"):
                            val = clean_currency_code(raw)
                        elif col_lower in int_cols:
                            val = clean_integer(raw)
                        elif col_lower in qty_cols or col_lower in numeric_cols:
                            val = clean_numeric(raw)
                        elif col_lower in date_cols:
                            val = parse_oracle_date(raw)
                        elif col_lower in strip_zero_cols:
                            val = strip_leading_zeros(raw)
                        else:
                            val = str(raw).strip() if raw is not None and str(raw).strip() != "" else None

                        if col_lower in strip_zero_cols and val is not None:
                            val = strip_leading_zeros(val)

                        normalized[col] = val

                    # --- Record Hash generation for audit ---
                    record_hash = generate_record_hash([normalized.get(h) for h in headers] + [str(row_num)])

                    # --- Build params tuple from mapped CSV columns ---
                    params_list = [normalized.get(h) for h in data_keys]

                    batch_values.append(tuple(params_list))
                    batch_meta.append({
                        "row_number":    row_num,
                        "hash":          record_hash,
                        "original_data": [row.get(h, "") for h in headers],
                    })

                    # --- Commit batch ---
                    if len(batch_values) >= settings.BATCH_SIZE:
                        ins, fails = self._commit_batch(
                            conn, insert_sql, headers, batch_values,
                            batch_meta, file_name, batch_id, target_table
                        )
                        inserted    += ins
                        failed_rows += fails
                        batch_values = []
                        batch_meta   = []
                        await self._send(batch_id, total_rows, processed,
                                         inserted, duplicates, len(failed_rows))
                        await asyncio.sleep(0)

                    # Light progress every 50 rows
                    elif processed % 50 == 0:
                        await self._send(batch_id, total_rows, processed,
                                         inserted, duplicates, len(failed_rows))
                        await asyncio.sleep(0)

                # Final partial batch
                if batch_values:
                    ins, fails = self._commit_batch(
                        conn, insert_sql, headers, batch_values,
                        batch_meta, file_name, batch_id, target_table
                    )
                    inserted    += ins
                    failed_rows += fails

        except (asyncio.CancelledError, KeyboardInterrupt):
            logger.info(f"Import process for batch {batch_id} cancelled during reload/shutdown.")
            if conn:
                try: conn.close()
                except: pass
            return
        except Exception as e:
            logger.error(f"Fatal import error: {e}", exc_info=True)
            await self._send(batch_id, total_rows, processed, inserted,
                             duplicates, len(failed_rows),
                             status="failed", msg=str(e))
            if conn:
                try: conn.close()
                except: pass
            return

        # ── 6. Automatically Run Finalize Data for target_table ─────────
        # Flow: Validate CSV -> Delete Existing -> Insert New Records -> Automatically Finalize Data -> Commit -> Show Result
        logger.info(f"Automatically running Finalize Data process for target table '{target_table}'...")
        try:
            finalize_res = finalize_service.process_finalize(target_table)
            logger.info(f"Auto-finalization completed for '{target_table}': {finalize_res}")
        except Exception as fe:
            logger.error(f"Auto-finalization exception for '{target_table}': {fe}", exc_info=True)

        # ── 7. Generate failed CSV log ────────────────────────────────────
        failed_log_file = generate_failed_log(file_name, failed_rows, headers)

        # ── 8. Update batch audit ─────────────────────────────────────────
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE CSV_IMPORT_BATCH SET
                        COMPLETED_AT      = SYSTIMESTAMP,
                        TOTAL_RECORDS     = :1,
                        PROCESSED_RECORDS = :2,
                        INSERTED_RECORDS  = :3,
                        DUPLICATE_RECORDS = :4,
                        FAILED_RECORDS    = :5,
                        STATUS            = 'COMPLETED',
                        FAILED_LOG_FILE   = :6
                    WHERE BATCH_ID = :7
                """, (total_rows, processed, inserted, duplicates,
                      len(failed_rows), failed_log_file, batch_id))
                conn.commit()
                cur.close()
            except Exception as e:
                logger.warning(f"Audit update failed: {e}")
            finally:
                try: conn.close()
                except: pass

        await self._send(batch_id, total_rows, processed, inserted,
                         duplicates, len(failed_rows), status="completed")

    # ─────────────────────────────────────────────────────────────────────────
    def _commit_batch(self, conn, sql, headers, batch_values,
                      batch_meta, file_name, batch_id, target_table):
        success_count = 0
        failed_batch  = []
        successful_meta = []

        if not conn:
            raise Exception("Database connection lost during batch commit.")

        cur = conn.cursor()
        try:
            for i, params in enumerate(batch_values):
                meta = batch_meta[i]
                try:
                    cur.execute(sql, params)
                    success_count += 1
                    successful_meta.append(meta)
                except Exception as e:
                    failed_batch.append({
                        "row_number":    meta["row_number"],
                        "error_message": str(e),
                        "error_type":    "DB_INSERT_ERROR",
                        "original_data": meta["original_data"],
                    })
                    logger.error(f"Row {meta['row_number']} insert error: {e}")

            conn.commit()

            # Batch-insert audit records for successfully inserted rows
            if successful_meta:
                audit_rows = [
                    (batch_id, file_name, target_table,
                     m["hash"], m["row_number"],
                     "INSERTED")
                    for m in successful_meta
                ]
                try:
                    cur.executemany("""
                        INSERT INTO CSV_IMPORT_RECORD_AUDIT
                            (BATCH_ID, IMPORT_TYPE, TARGET_TABLE, RECORD_HASH,
                             SOURCE_ROW_NUMBER, STATUS, PROCESSED_AT)
                        VALUES (:1, :2, :3, :4, :5, :6, SYSTIMESTAMP)
                    """, audit_rows)
                    conn.commit()
                except Exception as ae:
                    logger.warning(f"Audit batch insert failed: {ae}")

        except Exception as e:
            logger.error(f"Batch commit error: {e}", exc_info=True)
            try:
                conn.rollback()
            except Exception:
                pass
        finally:
            cur.close()

        return success_count, failed_batch

    # ─────────────────────────────────────────────────────────────────────────
    async def _send(self, job_id, total=0, processed=0, inserted=0,
                    duplicates=0, failed=0, status="processing", msg=""):
        pct = int((processed / total) * 100) if total > 0 else 0
        await progress_manager.send_progress(job_id, {
            "job_id":     job_id,
            "total":      total,
            "processed":  processed,
            "inserted":   inserted,
            "duplicates": duplicates,
            "failed":     failed,
            "percentage": pct,
            "status":     status,
            "message":    msg,
        })


csv_import_service = CSVImportService()
