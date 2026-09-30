import os
from datetime import datetime
import csv
import shutil

UPLOADS_DIR = "uploads/temp"
FAILED_LOGS_DIR = "logs/failed"

def save_upload_file(upload_file, filename):
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    filepath = os.path.join(UPLOADS_DIR, filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    return filepath

def generate_failed_log(file_name, failed_rows, headers):
    if not failed_rows:
        return None
    
    os.makedirs(FAILED_LOGS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%d%m%Y%H%M%S")
    base_name = os.path.splitext(os.path.basename(file_name))[0]
    failed_filename = f"failed_{base_name}_{timestamp}.csv"
    filepath = os.path.join(FAILED_LOGS_DIR, failed_filename)
    
    with open(filepath, "w", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["ROW_NUMBER", "ERROR_MESSAGE", "ERROR_TYPE"] + headers)
        for row in failed_rows:
            writer.writerow([row['row_number'], row['error_message'], row['error_type']] + row['original_data'])
            
    return failed_filename


def get_safe_file_reader(filepath: str):
    """
    Attempts to open a file with utf-8-sig first.
    If UnicodeDecodeError occurs (e.g. byte 0x92 / CP1252 smart quotes),
    falls back through cp1252, latin1, or utf-8 with errors='replace'.
    Returns an open file object.
    """
    encodings = ["utf-8-sig", "cp1252", "latin1"]
    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc) as test_f:
                for _ in test_f:
                    pass
            return open(filepath, "r", encoding=enc)
        except (UnicodeDecodeError, Exception):
            continue
    return open(filepath, "r", encoding="utf-8", errors="replace")

