from pydantic import BaseModel, Field
from typing import Optional

class DBConnectRequest(BaseModel):
    host: str = Field(default="10.5.1.144", description="Oracle Database Host IP/Hostname")
    port: int = Field(default=1540, description="Oracle Database Port")
    service: str = Field(default="MBLPRIMEODN", description="Oracle Database Service Name")
    username: str = Field(default="ultimus", description="Oracle Database Username")
    password: str = Field(default="ultimus123", description="Oracle Database Password")

class DBStatusResponse(BaseModel):
    connected: bool
    status_text: str
    host: Optional[str] = None
    port: Optional[int] = None
    service: Optional[str] = None
    username: Optional[str] = None
    message: Optional[str] = None
