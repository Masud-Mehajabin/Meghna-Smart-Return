import oracledb
import logging
from threading import Lock
from typing import Optional, Dict, Any, Tuple
from app.config import settings

logger = logging.getLogger(__name__)

class DBConnectionManager:
    """
    Centralized Runtime Database Connection Manager for Oracle Database.
    Manages dynamic connection settings provided securely by the user at runtime.
    """
    def __init__(self):
        self._lock = Lock()
        self._connected: bool = False
        self._config: Optional[Dict[str, Any]] = None
        self._last_error: Optional[str] = None
        self._attempt_initial_config()

    def _attempt_initial_config(self):
        """Optionally attempt to load from environment variables if present."""
        if settings.ORACLE_PASSWORD:
            self.connect(
                host=settings.ORACLE_HOST,
                port=settings.ORACLE_PORT,
                service=settings.ORACLE_SERVICE,
                username=settings.ORACLE_USERNAME,
                password=settings.ORACLE_PASSWORD
            )

    def connect(self, host: str, port: int, service: str, username: str, password: str) -> Tuple[bool, str]:
        """
        Attempt to establish an Oracle connection using the provided parameters.
        Tests the connection using `SELECT 1 FROM DUAL`.
        """
        if not host or not port or not service or not username or not password:
            return False, "All database connection parameters (Host, Port, Service, Username, Password) are required."

        dsn = f"{host.strip()}:{port}/{service.strip()}"
        
        try:
            logger.info(f"Attempting Oracle connection to DSN: {dsn} with User: {username}")
            connection = oracledb.connect(
                user=username.strip(),
                password=password,
                dsn=dsn,
                tcp_connect_timeout=6
            )
            
            # Connection validation test
            cursor = connection.cursor()
            cursor.execute("SELECT 1 FROM DUAL")
            result = cursor.fetchone()
            cursor.close()
            connection.close()

            if result and result[0] == 1:
                with self._lock:
                    self._connected = True
                    self._config = {
                        "host": host.strip(),
                        "port": int(port),
                        "service": service.strip(),
                        "username": username.strip(),
                        "password": password  # Kept securely in memory on backend only
                    }
                    self._last_error = None
                
                logger.info(f"Successfully connected to Oracle DB at {dsn}")
                
                # Attempt to initialize audit tables
                self._initialize_audit_tables()
                return True, f"Successfully connected to Oracle Database ({service.strip()} at {host.strip()}:{port})"
            else:
                return False, "Connection test failed: Unexpected response from SELECT 1 FROM DUAL."

        except oracledb.Error as oe:
            error_obj, = oe.args
            err_code = getattr(error_obj, 'code', None)
            err_msg = str(error_obj.message) if hasattr(error_obj, 'message') else str(oe)

            if err_code == 1017 or "ORA-01017" in err_msg:
                friendly_msg = "Invalid Username or Password (ORA-01017)."
            elif err_code == 12541 or "ORA-12541" in err_msg:
                friendly_msg = f"No listener found at {host}:{port} (ORA-12541). Check Host IP and Port."
            elif err_code == 12514 or "ORA-12514" in err_msg:
                friendly_msg = f"Service '{service}' not recognized by listener (ORA-12514). Check Service Name."
            elif "DPY-4000" in err_msg or "timeout" in err_msg.lower():
                friendly_msg = f"Network connection timed out while attempting to reach {host}:{port}."
            else:
                friendly_msg = f"Oracle Connection Error: {err_msg}"

            logger.error(f"Oracle connection error for user {username}: {friendly_msg}")
            with self._lock:
                self._connected = False
                self._last_error = friendly_msg
            return False, friendly_msg

        except Exception as e:
            friendly_msg = f"Connection Failed: {str(e)}"
            logger.error(f"General DB connection failure: {friendly_msg}")
            with self._lock:
                self._connected = False
                self._last_error = friendly_msg
            return False, friendly_msg

    def disconnect(self) -> Tuple[bool, str]:
        """Disconnect and clear connection parameters."""
        with self._lock:
            self._connected = False
            self._config = None
            self._last_error = None
        logger.info("Oracle database disconnected by user request.")
        return True, "Database disconnected successfully."

    def is_connected(self) -> bool:
        """Quickly check if the system considers itself connected."""
        with self._lock:
            return self._connected

    def get_status_info(self) -> Dict[str, Any]:
        """Returns connection status details without exposing password."""
        with self._lock:
            if not self._connected or not self._config:
                return {
                    "connected": False,
                    "status_text": "Disconnected",
                    "host": None,
                    "port": None,
                    "service": None,
                    "username": None,
                    "message": self._last_error or "Database is disconnected."
                }
            return {
                "connected": True,
                "status_text": "Connected",
                "host": self._config["host"],
                "port": self._config["port"],
                "service": self._config["service"],
                "username": self._config["username"],
                "message": f"Connected to {self._config['service']} as {self._config['username']}"
            }

    def get_raw_connection(self) -> Optional[oracledb.Connection]:
        """Returns a new active Oracle connection object using configured credentials."""
        with self._lock:
            if not self._connected or not self._config:
                return None
            config = dict(self._config)

        try:
            dsn = f"{config['host']}:{config['port']}/{config['service']}"
            connection = oracledb.connect(
                user=config['username'],
                password=config['password'],
                dsn=dsn,
                tcp_connect_timeout=6
            )
            return connection
        except Exception as e:
            logger.error(f"Failed to acquire database connection: {e}")
            with self._lock:
                self._connected = False
                self._last_error = f"Connection dropped: {str(e)}"
            return None

    def _initialize_audit_tables(self):
        """Create CSV_IMPORT_BATCH and CSV_IMPORT_RECORD_AUDIT if missing."""
        conn = self.get_raw_connection()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT count(*) FROM CSV_IMPORT_BATCH")
            except Exception:
                try:
                    cursor.execute("""
                        CREATE TABLE CSV_IMPORT_BATCH (
                            BATCH_ID VARCHAR2(50) PRIMARY KEY,
                            IMPORT_TYPE VARCHAR2(100),
                            SOURCE_FILE_NAME VARCHAR2(255),
                            TARGET_TABLE VARCHAR2(100),
                            FILE_HASH VARCHAR2(255),
                            STARTED_AT TIMESTAMP,
                            COMPLETED_AT TIMESTAMP,
                            TOTAL_RECORDS NUMBER,
                            PROCESSED_RECORDS NUMBER,
                            INSERTED_RECORDS NUMBER,
                            DUPLICATE_RECORDS NUMBER,
                            FAILED_RECORDS NUMBER,
                            STATUS VARCHAR2(50),
                            FAILED_LOG_FILE VARCHAR2(255),
                            ERROR_MESSAGE VARCHAR2(1000)
                        )
                    """)
                    cursor.execute("""
                        CREATE TABLE CSV_IMPORT_RECORD_AUDIT (
                            ID NUMBER GENERATED BY DEFAULT ON NULL AS IDENTITY PRIMARY KEY,
                            BATCH_ID VARCHAR2(50),
                            IMPORT_TYPE VARCHAR2(100),
                            TARGET_TABLE VARCHAR2(100),
                            RECORD_HASH VARCHAR2(255),
                            SOURCE_ROW_NUMBER NUMBER,
                            STATUS VARCHAR2(50),
                            ERROR_MESSAGE VARCHAR2(1000),
                            PROCESSED_AT TIMESTAMP
                        )
                    """)
                    cursor.execute("CREATE INDEX idx_csv_audit_hash ON CSV_IMPORT_RECORD_AUDIT(RECORD_HASH)")
                    conn.commit()
                    logger.info("Successfully created CSV audit tables.")
                except Exception as ex:
                    logger.error(f"Failed to create audit tables: {ex}")
            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"Error during audit table initialization: {e}")

db_manager = DBConnectionManager()
