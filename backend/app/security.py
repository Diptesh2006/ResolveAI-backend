from fastapi import Header, HTTPException
from .config import settings
def require_api_key(x_api_key: str | None = Header(default=None)):
    if x_api_key != settings.api_key: raise HTTPException(401, "Valid X-API-Key required")
def require_admin(x_admin_api_key: str | None = Header(default=None)):
    if x_admin_api_key != settings.admin_api_key: raise HTTPException(403, "Admin authorization required")
