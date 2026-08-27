from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app import models

router = APIRouter(prefix="/api/auth", tags=["auth"])

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login")
def login(form_data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.email).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token = create_access_token(subject=str(user.id))
    return {"access_token": access_token, "token_type": "bearer"}
