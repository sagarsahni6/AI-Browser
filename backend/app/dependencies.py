from fastapi import Header, HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from backend.app.config import settings

security = HTTPBearer(auto_error=False)

async def verify_local_token(
    x_local_token: Optional[str] = Header(None, alias="X-Local-Token"),
    auth: Optional[HTTPAuthorizationCredentials] = Security(security)
):
    # Check header token or bearer token
    token = x_local_token or (auth.credentials if auth else None)

    # In local testing, if token is provided, it must match SECRET_TOKEN
    if settings.SECRET_TOKEN and settings.SECRET_TOKEN != "local-dev-secret-token":
        if not token or token != settings.SECRET_TOKEN:
            raise HTTPException(status_code=401, detail="Unauthorized: invalid local authentication token")

    return True
