# CSV Data Integration & Validation System (Meghna Smart Return)

Production-grade FastAPI CSV Import Automation & Database System for Oracle Database.

## Features & Highlights

- **Strict File-to-Table Mapping**: 6 predefined upload modules strictly mapped to assigned Oracle database tables (`A1_O1`, `ARV`, `E2_P2`, `C_FORM`, `E3_P3`, `BBRETURN_MANUAL_TM`). Backend enforces mapping; users cannot select arbitrary destination tables.
- **Zero-Precision-Loss Scientific Notation Conversion**: All scientific notation inputs (e.g. `2.10111E+14`) are read as raw text and normalized using Python `decimal.Decimal` into exact strings (`210111000000000`) without floating-point precision loss. Leading zeros on identifier columns are preserved.
- **Persistent Database-Backed Duplicate Prevention**: Queries target Oracle DB tables and `CSV_IMPORT_RECORD_AUDIT` to calculate SHA-256 business key hashes and eliminate duplicate inserts across application restarts and partial file uploads.
- **Real-Time WebSocket Progress**: Broadcasts live processing stats (`total`, `processed`, `inserted`, `duplicates`, `failed`, `percentage`, `status`) to the UI progress bars.
- **Timestamped Failed Record Logging**: Generates dedicated failed CSV log files (`failed_<name>_<DDMMYYYYHHMMSS>.csv`) preserving original row data and row numbers for easy correction.
- **Glassmorphism UI Dashboard**: Pure CSS glass-styled dark mode interface with state locking controls, completion modals, and import history viewer.

---

## 6 Predefined Import Mappings

| CSV File Name | Target Oracle Table | Business Key | Scientific Columns |
| :--- | :--- | :--- | :--- |
| `triplicate_list.csv` | `A1_O1` | `EXP No` | `EXP No`, `ERC No` |
| `online_reported_arv_list.csv` | `ARV` | `ARV ID` | `ARV ID`, `HSCode`, `ERC No.` |
| `e2-p2_rit_imp_report.csv` | `E2_P2` | `LC ID`, `IMP No` | `LC ID`, `IMP No`, `IRC No` |
| `c_form_summary.csv` | `C_FORM` | `CFORMID`, `UNIQUE_ID` | `CFORMID`, `UNIQUE_ID` |
| `report_tm_main_for_bank_ho.csv` | `E3_P3` | `ID_TMF` | `ID_TMF`, `UNIQUE_ID` |
| `details_tm_data_from_imp_entry_(tm_date_wise).csv` | `BBRETURN_MANUAL_TM` | `ID_TMF` | `ID_TMF`, `Lc Id`, `IMP No` |

---

## Setup Instructions

1. **Prerequisites**:
   - Python 3.12+
   - Access to Oracle Database instance

2. **Installation**:
   ```bash
   cd f:\BBreturn\csv_import_automation
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and fill in credentials:
   ```ini
   ORACLE_HOST=10.5.1.144
   ORACLE_PORT=1540
   ORACLE_SERVICE=MBLPRIMEODN
   ORACLE_USERNAME=masud
   ORACLE_PASSWORD=your_password_here
   BATCH_SIZE=500
   ```

4. **Run Server**:
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

5. **Access Application**:
   Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.
