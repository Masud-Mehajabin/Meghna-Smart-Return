import oracledb
from contextlib import contextmanager
from app.services.db_manager import db_manager
import logging

logger = logging.getLogger(__name__)


def get_connection():
    """Return an active oracledb connection managed by db_manager."""
    return db_manager.get_raw_connection()


@contextmanager
def get_db_cursor():
    """Context-manager that yields a cursor from the active db connection."""
    connection = get_connection()
    if not connection:
        yield None
        return

    cursor = connection.cursor()
    try:
        yield cursor
        connection.commit()
    except Exception as e:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def check_db_connection() -> bool:
    return db_manager.is_connected()
