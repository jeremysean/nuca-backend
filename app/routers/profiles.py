from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from datetime import date
from app.database import get_db
from app.security.auth import get_current_user, AuthService
from app.security.encryption import encrypt_profile_health_data, decrypt_profile_health_data, encryption_service
from app.models import User, Profile, ProfileAllergen, Allergen, ConsentTypeEnum, AuditLog
from app.schemas import (
    ProfileCreate, ProfileUpdate, ProfileResponse, ProfileLimitsResponse,
    AllergenAddRequest, ProfileAllergenResponse
)
from app.services.limits_engine import PersonalLimitsEngine


router = APIRouter(prefix="/api/v1/profiles", tags=["Profiles"])


def build_profile_response(profile_db: Profile, db: Session) -> ProfileResponse:
    decrypted = decrypt_profile_health_data(profile_db)
    
    limits_response = None
    if all([
        profile_db.daily_eer_kcal,
        profile_db.daily_sugar_hard_g,
        profile_db.daily_sodium_hard_mg,
        profile_db.daily_satfat_hard_g
    ]):
        limits_response = ProfileLimitsResponse(
            eer_kcal=float(profile_db.daily_eer_kcal),
            sugar_soft_g=float(profile_db.daily_sugar_soft_g),
            sugar_hard_g=float(profile_db.daily_sugar_hard_g),
            sodium_soft_mg=float(profile_db.daily_sodium_soft_mg),
            sodium_hard_mg=float(profile_db.daily_sodium_hard_mg),
            satfat_soft_g=float(profile_db.daily_satfat_soft_g),
            satfat_hard_g=float(profile_db.daily_satfat_hard_g),
            transfat_hard_g=float(profile_db.daily_transfat_hard_g),
            flags={}
        )
    
    return ProfileResponse(
        id=profile_db.id,
        user_id=profile_db.user_id,
        name=profile_db.name,
        date_of_birth=decrypted.get("date_of_birth"),
        sex=profile_db.sex,
        height_cm=decrypted.get("height_cm"),
        weight_kg=decrypted.get("weight_kg"),
        activity_level=profile_db.activity_level,
        has_hypertension=decrypted.get("has_hypertension"),
        has_diabetes=decrypted.get("has_diabetes"),
        has_heart_disease=decrypted.get("has_heart_disease"),
        has_kidney_disease=decrypted.get("has_kidney_disease"),
        is_pregnant=decrypted.get("is_pregnant"),
        goal_primary=profile_db.goal_primary,
        limits=limits_response,
        created_at=profile_db.created_at,
        updated_at=profile_db.updated_at
    )


@router.post("/", response_model=ProfileResponse, status_code=201)
async def create_profile(
    profile_data: ProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    AuthService.require_consent(
        str(current_user.id),
        ConsentTypeEnum.health_data_processing,
        db
    )
    
    profile_dict = profile_data.dict()
    encrypted_data = encrypt_profile_health_data(profile_dict)
    
    limits = PersonalLimitsEngine.compute_personal_limits(
        date_of_birth=profile_data.date_of_birth,
        sex=profile_data.sex.value,
        height_cm=profile_data.height_cm,
        weight_kg=profile_data.weight_kg,
        activity_level=profile_data.activity_level.value,
        has_hypertension=profile_data.has_hypertension,
        has_diabetes=profile_data.has_diabetes,
        has_heart_disease=profile_data.has_heart_disease,
        has_kidney_disease=profile_data.has_kidney_disease,
        is_pregnant=profile_data.is_pregnant
    )
    
    profile = Profile(
        user_id=current_user.id,
        name=encrypted_data["name"],
        sex=encrypted_data["sex"],
        activity_level=encrypted_data["activity_level"],
        goal_primary=encrypted_data.get("goal_primary"),
        date_of_birth_encrypted=encrypted_data.get("date_of_birth_encrypted"),
        height_cm_encrypted=encrypted_data.get("height_cm_encrypted"),
        weight_kg_encrypted=encrypted_data.get("weight_kg_encrypted"),
        has_hypertension_encrypted=encrypted_data.get("has_hypertension_encrypted"),
        has_diabetes_encrypted=encrypted_data.get("has_diabetes_encrypted"),
        has_heart_disease_encrypted=encrypted_data.get("has_heart_disease_encrypted"),
        has_kidney_disease_encrypted=encrypted_data.get("has_kidney_disease_encrypted"),
        is_pregnant_encrypted=encrypted_data.get("is_pregnant_encrypted"),
        daily_eer_kcal=limits.eer_kcal,
        daily_sugar_soft_g=limits.sugar_soft_g,
        daily_sugar_hard_g=limits.sugar_hard_g,
        daily_sodium_soft_mg=limits.sodium_soft_mg,
        daily_sodium_hard_mg=limits.sodium_hard_mg,
        daily_satfat_soft_g=limits.satfat_soft_g,
        daily_satfat_hard_g=limits.satfat_hard_g,
        daily_transfat_hard_g=limits.transfat_hard_g
    )
    
    db.add(profile)
    db.commit()
    db.refresh(profile)
    
    audit = AuditLog(
        user_id=current_user.id,
        action="profile_created",
        resource_type="profile",
        resource_id=profile.id
    )
    db.add(audit)
    db.commit()
    
    return build_profile_response(profile, db)


@router.get("/", response_model=List[ProfileResponse])
async def list_profiles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profiles = db.query(Profile).filter(Profile.user_id == current_user.id).all()
    return [build_profile_response(p, db) for p in profiles]


@router.get("/{profile_id}", response_model=ProfileResponse)
async def get_profile(
    profile_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(Profile).filter(
        Profile.id == profile_id,
        Profile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return build_profile_response(profile, db)


@router.put("/{profile_id}", response_model=ProfileResponse)
async def update_profile(
    profile_id: UUID,
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(Profile).filter(
        Profile.id == profile_id,
        Profile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    update_dict = profile_data.dict(exclude_unset=True)
    
    if update_dict:
        encrypted_updates = encrypt_profile_health_data(update_dict)
        
        for key, value in encrypted_updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        
        decrypted_current = decrypt_profile_health_data(profile)
        
        limits = PersonalLimitsEngine.compute_personal_limits(
            date_of_birth=decrypted_current.get("date_of_birth") or date.today(),
            sex=profile.sex.value if profile.sex else "other",
            height_cm=decrypted_current.get("height_cm"),
            weight_kg=decrypted_current.get("weight_kg"),
            activity_level=profile.activity_level.value,
            has_hypertension=decrypted_current.get("has_hypertension", False),
            has_diabetes=decrypted_current.get("has_diabetes", False),
            has_heart_disease=decrypted_current.get("has_heart_disease", False),
            has_kidney_disease=decrypted_current.get("has_kidney_disease", False),
            is_pregnant=decrypted_current.get("is_pregnant", False)
        )
        
        profile.daily_eer_kcal = limits.eer_kcal
        profile.daily_sugar_soft_g = limits.sugar_soft_g
        profile.daily_sugar_hard_g = limits.sugar_hard_g
        profile.daily_sodium_soft_mg = limits.sodium_soft_mg
        profile.daily_sodium_hard_mg = limits.sodium_hard_mg
        profile.daily_satfat_soft_g = limits.satfat_soft_g
        profile.daily_satfat_hard_g = limits.satfat_hard_g
        profile.daily_transfat_hard_g = limits.transfat_hard_g
        
        db.commit()
        db.refresh(profile)
        
        audit = AuditLog(
            user_id=current_user.id,
            action="profile_updated",
            resource_type="profile",
            resource_id=profile.id
        )
        db.add(audit)
        db.commit()
    
    return build_profile_response(profile, db)


@router.delete("/{profile_id}", status_code=204)
async def delete_profile(
    profile_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(Profile).filter(
        Profile.id == profile_id,
        Profile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    audit = AuditLog(
        user_id=current_user.id,
        action="profile_deleted",
        resource_type="profile",
        resource_id=profile.id
    )
    db.add(audit)
    
    db.delete(profile)
    db.commit()
    
    return None


@router.post("/{profile_id}/allergens", response_model=ProfileAllergenResponse, status_code=201)
async def add_allergen_to_profile(
    profile_id: UUID,
    allergen_data: AllergenAddRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(Profile).filter(
        Profile.id == profile_id,
        Profile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    allergen = db.query(Allergen).filter(Allergen.code == allergen_data.allergen_code).first()
    if not allergen:
        raise HTTPException(status_code=404, detail="Allergen not found")
    
    existing = db.query(ProfileAllergen).filter(
        ProfileAllergen.profile_id == profile_id,
        ProfileAllergen.allergen_id == allergen.id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Allergen already added to profile")
    
    profile_allergen = ProfileAllergen(
        profile_id=profile_id,
        allergen_id=allergen.id,
        severity=allergen_data.severity
    )
    
    db.add(profile_allergen)
    db.commit()
    db.refresh(profile_allergen)
    
    return ProfileAllergenResponse(
        id=profile_allergen.id,
        allergen=allergen,
        severity=profile_allergen.severity
    )


@router.get("/{profile_id}/allergens", response_model=List[ProfileAllergenResponse])
async def list_profile_allergens(
    profile_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(Profile).filter(
        Profile.id == profile_id,
        Profile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    allergens = db.query(ProfileAllergen).filter(
        ProfileAllergen.profile_id == profile_id
    ).all()
    
    return [
        ProfileAllergenResponse(
            id=pa.id,
            allergen=pa.allergen,
            severity=pa.severity
        )
        for pa in allergens
    ]


@router.delete("/{profile_id}/allergens/{allergen_id}", status_code=204)
async def remove_allergen_from_profile(
    profile_id: UUID,
    allergen_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(Profile).filter(
        Profile.id == profile_id,
        Profile.user_id == current_user.id
    ).first()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile_allergen = db.query(ProfileAllergen).filter(
        ProfileAllergen.profile_id == profile_id,
        ProfileAllergen.allergen_id == allergen_id
    ).first()
    
    if not profile_allergen:
        raise HTTPException(status_code=404, detail="Allergen not found in profile")
    
    db.delete(profile_allergen)
    db.commit()
    
    return None
