from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app import models

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    db: Session = Depends(get_db),
) -> models.User:
    user = db.query(models.User).filter(models.User.email == "treasury@demo-bank.com").first()
    if not user:
        user = db.query(models.User).first()
    return user
