from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .security import decode_token

bearer = HTTPBearer(auto_error=False)

async def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    if not creds:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = decode_token(creds.credentials)
    except Exception:
        raise HTTPException(401, "Invalid token")
    return payload  # {sub, role}

def require_role(*roles: str):
    def _checker(user = Depends(get_current_user)):
        if user.get("role") not in roles:
            raise HTTPException(403, "Forbidden")
        return user
    return _checker
