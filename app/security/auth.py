from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from datetime import datetime, timedelta
from app.config import settings
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, UserConsent, ConsentTypeEnum
import hashlib


security = HTTPBearer()


class AuthService:
    @staticmethod
    def verify_supabase_token(token: str) -> dict:
        try:
            payload = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                options={"verify_aud": False}
            )
            return payload
        except JWTError as e:
            raise HTTPException(
                status_code=401,
                detail=f"Invalid authentication token: {str(e)}"
            )
    
    @staticmethod
    def get_current_user_id(
        credentials: HTTPAuthorizationCredentials = Security(security),
        db: Session = Depends(get_db)
    ) -> str:
        token = credentials.credentials
        payload = AuthService.verify_supabase_token(token)
        
        supabase_user_id = payload.get("sub")
        if not supabase_user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        user = db.query(User).filter(User.supabase_user_id == supabase_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not user.is_active:
            raise HTTPException(status_code=403, detail="User account is deactivated")
        
        user.last_login_at = datetime.utcnow()
        db.commit()
        
        return str(user.id)
    
    @staticmethod
    def check_consent(
        user_id: str,
        consent_type: ConsentTypeEnum,
        db: Session
    ) -> bool:
        consent = db.query(UserConsent).filter(
            UserConsent.user_id == user_id,
            UserConsent.consent_type == consent_type,
            UserConsent.granted == True,
            UserConsent.revoked_at.is_(None)
        ).first()
        
        return consent is not None
    
    @staticmethod
    def require_consent(
        user_id: str,
        consent_type: ConsentTypeEnum,
        db: Session
    ):
        if not AuthService.check_consent(user_id, consent_type, db):
            raise HTTPException(
                status_code=403,
                detail=f"This operation requires '{consent_type.value}' consent. Please grant consent in app settings."
            )
    
    @staticmethod
    def hash_ip(ip_address: str) -> str:
        return hashlib.sha256(ip_address.encode()).hexdigest()
    
    @staticmethod
    def hash_user_agent(user_agent: str) -> str:
        return hashlib.sha256(user_agent.encode()).hexdigest()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials
    payload = AuthService.verify_supabase_token(token)
    
    supabase_user_id = payload.get("sub")
    if not supabase_user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    user = db.query(User).filter(User.supabase_user_id == supabase_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is deactivated")
    
    user.last_login_at = datetime.utcnow()
    db.commit()
    
    return user
