from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.security.auth import get_current_user
from app.models import User
from datetime import datetime

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

@router.post("/initialize-user")
async def initialize_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Called after successful OAuth to ensure user exists in our database
    """
    print(f"Initializing user: {current_user.id}, Active: {current_user.is_active}")
    current_user.last_login_at = datetime.utcnow()
    db.commit()
    
    return {
        "user_id": str(current_user.id),
        "display_name": current_user.display_name,
        "has_profile": len(current_user.profiles) > 0
    }