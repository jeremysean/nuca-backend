from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.database import get_db
from app.security.auth import get_current_user, AuthService
from app.models import User, UserConsent, ConsentTypeEnum, AuditLog
from app.schemas import ConsentCreate, ConsentResponse


router = APIRouter(prefix="/api/v1/consent", tags=["Consent Management"])


@router.post("", response_model=ConsentResponse, status_code=201)
async def grant_or_revoke_consent(
    consent_data: ConsentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    existing_consent = db.query(UserConsent).filter(
        UserConsent.user_id == current_user.id,
        UserConsent.consent_type == consent_data.consent_type
    ).first()
    
    if existing_consent:
        if consent_data.granted:
            existing_consent.granted = True
            existing_consent.granted_at = datetime.utcnow()
            existing_consent.revoked_at = None
        else:
            existing_consent.granted = False
            existing_consent.revoked_at = datetime.utcnow()
        
        if consent_data.ip_address:
            existing_consent.ip_address_hash = AuthService.hash_ip(consent_data.ip_address)
        if consent_data.user_agent:
            existing_consent.user_agent_hash = AuthService.hash_user_agent(consent_data.user_agent)
        
        db.commit()
        db.refresh(existing_consent)
        consent = existing_consent
    else:
        consent = UserConsent(
            user_id=current_user.id,
            consent_type=consent_data.consent_type,
            granted=consent_data.granted,
            granted_at=datetime.utcnow() if consent_data.granted else None,
            ip_address_hash=AuthService.hash_ip(consent_data.ip_address) if consent_data.ip_address else None,
            user_agent_hash=AuthService.hash_user_agent(consent_data.user_agent) if consent_data.user_agent else None
        )
        db.add(consent)
        db.commit()
        db.refresh(consent)
    
    audit = AuditLog(
        user_id=current_user.id,
        action="consent_updated",
        resource_type="user_consent",
        resource_id=consent.id,
        metadata={
            "consent_type": consent_data.consent_type.value,
            "granted": consent_data.granted
        }
    )
    db.add(audit)
    db.commit()
    
    return consent


@router.get("", response_model=List[ConsentResponse])
async def list_user_consents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    consents = db.query(UserConsent).filter(
        UserConsent.user_id == current_user.id
    ).all()
    
    return consents


@router.get("/{consent_type}", response_model=ConsentResponse)
async def get_consent_status(
    consent_type: ConsentTypeEnum,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    consent = db.query(UserConsent).filter(
        UserConsent.user_id == current_user.id,
        UserConsent.consent_type == consent_type
    ).first()
    
    if not consent:
        return ConsentResponse(
            id=None,
            consent_type=consent_type,
            granted=False,
            granted_at=None,
            consent_version="1.0"
        )
    
    return consent
