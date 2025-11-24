from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from app.database import get_db
from app.security.auth import get_current_user, AuthService
from app.security.encryption import encryption_service
from app.models import User, FamilyMember, ConsentTypeEnum, AuditLog
from app.schemas import FamilyMemberCreate, FamilyMemberResponse, ProfileLimitsResponse
from app.services.limits_engine import PersonalLimitsEngine
import json


router = APIRouter(prefix="/api/v1/family-members", tags=["Family Members"])


def build_family_member_response(member_db: FamilyMember) -> FamilyMemberResponse:
    dob = None
    if member_db.date_of_birth_encrypted:
        from datetime import date
        dob_str = encryption_service.decrypt(member_db.date_of_birth_encrypted)
        dob = date.fromisoformat(dob_str)
    
    height_cm = encryption_service.decrypt_decimal(member_db.height_cm_encrypted) if member_db.height_cm_encrypted else None
    weight_kg = encryption_service.decrypt_decimal(member_db.weight_kg_encrypted) if member_db.weight_kg_encrypted else None
    
    health_flags = {}
    if member_db.health_flags_encrypted:
        health_json = encryption_service.decrypt(member_db.health_flags_encrypted)
        health_flags = json.loads(health_json)
    
    limits_response = None
    if member_db.daily_eer_kcal:
        limits_response = ProfileLimitsResponse(
            eer_kcal=float(member_db.daily_eer_kcal),
            sugar_soft_g=float(member_db.daily_sugar_soft_g),
            sugar_hard_g=float(member_db.daily_sugar_hard_g),
            sodium_soft_mg=float(member_db.daily_sodium_soft_mg),
            sodium_hard_mg=float(member_db.daily_sodium_hard_mg),
            satfat_soft_g=float(member_db.daily_satfat_soft_g),
            satfat_hard_g=float(member_db.daily_satfat_hard_g),
            transfat_hard_g=float(member_db.daily_transfat_hard_g),
            flags={}
        )
    
    return FamilyMemberResponse(
        id=member_db.id,
        owner_user_id=member_db.owner_user_id,
        name=member_db.name,
        relationship=member_db.relationship,
        date_of_birth=dob,
        sex=member_db.sex,
        height_cm=height_cm,
        weight_kg=weight_kg,
        activity_level=member_db.activity_level,
        health_flags=health_flags,
        is_default=member_db.is_default,
        limits=limits_response,
        created_at=member_db.created_at
    )


@router.post("", response_model=FamilyMemberResponse, status_code=201)
async def create_family_member(
    member_data: FamilyMemberCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    AuthService.require_consent(
        str(current_user.id),
        ConsentTypeEnum.family_data_processing,
        db
    )
    
    dob_encrypted = encryption_service.encrypt(member_data.date_of_birth.isoformat())
    height_encrypted = encryption_service.encrypt_decimal(member_data.height_cm) if member_data.height_cm else None
    weight_encrypted = encryption_service.encrypt_decimal(member_data.weight_kg) if member_data.weight_kg else None
    health_encrypted = encryption_service.encrypt(json.dumps(member_data.health_flags))
    
    limits = PersonalLimitsEngine.compute_personal_limits(
        date_of_birth=member_data.date_of_birth,
        sex=member_data.sex.value,
        height_cm=member_data.height_cm,
        weight_kg=member_data.weight_kg,
        activity_level=member_data.activity_level.value,
        has_hypertension=member_data.health_flags.get("has_hypertension", False),
        has_diabetes=member_data.health_flags.get("has_diabetes", False),
        has_heart_disease=member_data.health_flags.get("has_heart_disease", False),
        has_kidney_disease=member_data.health_flags.get("has_kidney_disease", False),
        is_pregnant=member_data.health_flags.get("is_pregnant", False)
    )
    
    member = FamilyMember(
        owner_user_id=current_user.id,
        name=member_data.name,
        relationship=member_data.relationship,
        sex=member_data.sex,
        activity_level=member_data.activity_level,
        is_default=member_data.is_default,
        date_of_birth_encrypted=dob_encrypted,
        height_cm_encrypted=height_encrypted,
        weight_kg_encrypted=weight_encrypted,
        health_flags_encrypted=health_encrypted,
        daily_eer_kcal=limits.eer_kcal,
        daily_sugar_soft_g=limits.sugar_soft_g,
        daily_sugar_hard_g=limits.sugar_hard_g,
        daily_sodium_soft_mg=limits.sodium_soft_mg,
        daily_sodium_hard_mg=limits.sodium_hard_mg,
        daily_satfat_soft_g=limits.satfat_soft_g,
        daily_satfat_hard_g=limits.satfat_hard_g,
        daily_transfat_hard_g=limits.transfat_hard_g
    )
    
    db.add(member)
    db.commit()
    db.refresh(member)
    
    audit = AuditLog(
        user_id=current_user.id,
        action="family_member_created",
        resource_type="family_member",
        resource_id=member.id
    )
    db.add(audit)
    db.commit()
    
    return build_family_member_response(member)


@router.get("", response_model=List[FamilyMemberResponse])
async def list_family_members(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    members = db.query(FamilyMember).filter(
        FamilyMember.owner_user_id == current_user.id
    ).all()
    
    return [build_family_member_response(m) for m in members]


@router.get("/{member_id}", response_model=FamilyMemberResponse)
async def get_family_member(
    member_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    member = db.query(FamilyMember).filter(
        FamilyMember.id == member_id,
        FamilyMember.owner_user_id == current_user.id
    ).first()
    
    if not member:
        raise HTTPException(status_code=404, detail="Family member not found")
    
    return build_family_member_response(member)


@router.delete("/{member_id}", status_code=204)
async def delete_family_member(
    member_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    member = db.query(FamilyMember).filter(
        FamilyMember.id == member_id,
        FamilyMember.owner_user_id == current_user.id
    ).first()
    
    if not member:
        raise HTTPException(status_code=404, detail="Family member not found")
    
    audit = AuditLog(
        user_id=current_user.id,
        action="family_member_deleted",
        resource_type="family_member",
        resource_id=member.id
    )
    db.add(audit)
    
    db.delete(member)
    db.commit()
    
    return None
