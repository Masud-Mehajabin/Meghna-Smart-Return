import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    ORACLE_HOST = os.getenv("ORACLE_HOST", "10.5.1.144")
    ORACLE_PORT = os.getenv("ORACLE_PORT", "1540")
    ORACLE_SERVICE = os.getenv("ORACLE_SERVICE", "MBLPRI")
    ORACLE_USERNAME = os.getenv("ORACLE_USERNAME", "masud")
    ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD", "")
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", "500"))

settings = Settings()
