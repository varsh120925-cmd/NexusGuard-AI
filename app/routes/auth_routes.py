"""
Authentication REST API Routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.auth_schemas import UserRegister, UserLogin, TokenResponse, UserResponse
from app.services.auth_service import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user
)

router = APIRouter(prefix="/api", tags=["Authentication"])

@router.post("/register", response_model=TokenResponse)
def register(user_in: UserRegister, response: Response, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    new_user = User(
        name=user_in.name,
        email=user_in.email.lower(),
        hashed_password=get_password_hash(user_in.password),
        role=user_in.role or "Logistics Operations Lead"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token(data={"sub": new_user.email, "user_id": new_user.id, "name": new_user.name})
    response.set_cookie(key="access_token", value=token, httponly=True, max_age=86400, samesite="lax")

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_name=new_user.name,
        user_email=new_user.email,
        user_role=new_user.role
    )

@router.post("/login", response_model=TokenResponse)
def login(login_in: UserLogin, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_in.email.lower()).first()
    if not user or not verify_password(login_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password credentials."
        )

    token = create_access_token(data={"sub": user.email, "user_id": user.id, "name": user.name})
    response.set_cookie(key="access_token", value=token, httponly=True, max_age=86400, samesite="lax")

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_name=user.name,
        user_email=user.email,
        user_role=user.role
    )

@router.get("/me", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Logged out successfully."}
