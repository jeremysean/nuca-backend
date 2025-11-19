from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List
from datetime import date, datetime
from uuid import UUID
from app.models import (
    SexEnum, ActivityLevelEnum, GoalEnum, RelationshipEnum,
    GradeEnum, SeverityEnum, ConsentTypeEnum
)


class ConsentCreate(BaseModel):
    consent_type: ConsentTypeEnum
    granted: bool
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class ConsentResponse(BaseModel):
    id: UUID
    consent_type: ConsentTypeEnum
    granted: bool
    granted_at: Optional[datetime]
    consent_version: str
    
    class Config:
        from_attributes = True


class ProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    date_of_birth: date
    sex: SexEnum
    height_cm: Optional[float] = Field(None, ge=50, le=250)
    weight_kg: Optional[float] = Field(None, ge=10, le=300)
    activity_level: ActivityLevelEnum = ActivityLevelEnum.sedentary
    has_hypertension: bool = False
    has_diabetes: bool = False
    has_heart_disease: bool = False
    has_kidney_disease: bool = False
    is_pregnant: bool = False
    goal_primary: Optional[GoalEnum] = None
    
    @validator('date_of_birth')
    def validate_age(cls, v):
        today = date.today()
        age_years = (today - v).days / 365.25
        if age_years < 0 or age_years > 120:
            raise ValueError('Invalid date of birth')
        return v


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    date_of_birth: Optional[date] = None
    sex: Optional[SexEnum] = None
    height_cm: Optional[float] = Field(None, ge=50, le=250)
    weight_kg: Optional[float] = Field(None, ge=10, le=300)
    activity_level: Optional[ActivityLevelEnum] = None
    has_hypertension: Optional[bool] = None
    has_diabetes: Optional[bool] = None
    has_heart_disease: Optional[bool] = None
    has_kidney_disease: Optional[bool] = None
    is_pregnant: Optional[bool] = None
    goal_primary: Optional[GoalEnum] = None


class ProfileLimitsResponse(BaseModel):
    eer_kcal: float
    sugar_soft_g: float
    sugar_hard_g: float
    sodium_soft_mg: float
    sodium_hard_mg: float
    satfat_soft_g: float
    satfat_hard_g: float
    transfat_hard_g: float
    flags: dict


class ProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    date_of_birth: Optional[date]
    sex: Optional[SexEnum]
    height_cm: Optional[float]
    weight_kg: Optional[float]
    activity_level: ActivityLevelEnum
    has_hypertension: Optional[bool]
    has_diabetes: Optional[bool]
    has_heart_disease: Optional[bool]
    has_kidney_disease: Optional[bool]
    is_pregnant: Optional[bool]
    goal_primary: Optional[GoalEnum]
    limits: Optional[ProfileLimitsResponse]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class FamilyMemberCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    relationship: RelationshipEnum
    date_of_birth: date
    sex: SexEnum
    height_cm: Optional[float] = Field(None, ge=50, le=250)
    weight_kg: Optional[float] = Field(None, ge=10, le=300)
    activity_level: ActivityLevelEnum = ActivityLevelEnum.sedentary
    health_flags: Optional[dict] = {}
    is_default: bool = False


class FamilyMemberResponse(BaseModel):
    id: UUID
    owner_user_id: UUID
    name: str
    relationship: RelationshipEnum
    date_of_birth: Optional[date]
    sex: Optional[SexEnum]
    height_cm: Optional[float]
    weight_kg: Optional[float]
    activity_level: ActivityLevelEnum
    health_flags: Optional[dict]
    is_default: bool
    limits: Optional[ProfileLimitsResponse]
    created_at: datetime
    
    class Config:
        from_attributes = True


class AllergenAddRequest(BaseModel):
    allergen_code: str
    severity: SeverityEnum = SeverityEnum.moderate


class AllergenResponse(BaseModel):
    id: UUID
    code: str
    name: str
    description: Optional[str]
    
    class Config:
        from_attributes = True


class ProfileAllergenResponse(BaseModel):
    id: UUID
    allergen: AllergenResponse
    severity: SeverityEnum
    
    class Config:
        from_attributes = True


class ProductNutritionResponse(BaseModel):
    per_100g_energy_kcal: Optional[float]
    per_100g_fat_g: Optional[float]
    per_100g_saturated_fat_g: Optional[float]
    per_100g_carbs_g: Optional[float]
    per_100g_sugars_g: Optional[float]
    per_100g_protein_g: Optional[float]
    per_100g_fiber_g: Optional[float]
    per_100g_sodium_mg: Optional[float]
    per_serving_energy_kcal: Optional[float]
    per_serving_sugars_g: Optional[float]
    per_serving_sodium_mg: Optional[float]
    per_serving_saturated_fat_g: Optional[float]
    
    class Config:
        from_attributes = True


class ProductIngredientResponse(BaseModel):
    name_raw: str
    is_additive: bool
    additive_code: Optional[str]
    
    class Config:
        from_attributes = True


class ProductAllergenTagResponse(BaseModel):
    allergen: AllergenResponse
    contain_type: str
    
    class Config:
        from_attributes = True


class ProductGradingResult(BaseModel):
    grade: GradeEnum
    sugar_zone: str
    sodium_zone: str
    satfat_zone: str
    dangerous_nutrients_count: int
    sugar_pct_of_limit: float
    sodium_pct_of_limit: float
    satfat_pct_of_limit: float
    additive_count: int
    nova_group: Optional[int]
    allergen_matches: List[ProductAllergenTagResponse] = []
    warnings: List[str] = []


class ProductDetailResponse(BaseModel):
    id: UUID
    barcode: Optional[str]
    name: str
    brand: Optional[str]
    image_url: Optional[str]
    serving_size_label: Optional[str]
    nova_group: Optional[int]
    nutrition: Optional[ProductNutritionResponse]
    ingredients: List[ProductIngredientResponse] = []
    allergen_tags: List[ProductAllergenTagResponse] = []
    grading: Optional[ProductGradingResult]
    
    class Config:
        from_attributes = True


class ScanBarcodeRequest(BaseModel):
    barcode: str = Field(..., min_length=8, max_length=20)
    profile_id: Optional[UUID] = None
    family_member_id: Optional[UUID] = None


class ScanBarcodeResponse(BaseModel):
    status: str
    product: Optional[ProductDetailResponse]
    suggest_add: bool = False
    message: Optional[str] = None


class ConsumptionLogCreate(BaseModel):
    scan_session_id: UUID
    serving_multiplier: float = Field(1.0, ge=0.1, le=10.0)


class ConsumptionLogResponse(BaseModel):
    id: UUID
    scan_session_id: UUID
    profile_id: Optional[UUID]
    family_member_id: Optional[UUID]
    serving_multiplier: float
    consumed_at: datetime
    
    class Config:
        from_attributes = True


class NutrientSummary(BaseModel):
    consumed_g_or_mg: float
    limit_g_or_mg: float
    percentage: float
    zone: str


class AnalyticsSummaryResponse(BaseModel):
    period: str
    profile_id: Optional[UUID]
    family_member_id: Optional[UUID]
    sugar: NutrientSummary
    sodium: NutrientSummary
    saturated_fat: NutrientSummary
    consumption_count: int
    grade_distribution: dict


class ProductSuggestionCreate(BaseModel):
    barcode: Optional[str] = None
    front_image_url: str
    nutrition_label_image_url: Optional[str]
    ingredients_image_url: Optional[str]


class ProductSuggestionResponse(BaseModel):
    id: UUID
    barcode: Optional[str]
    front_image_url: str
    nutrition_label_image_url: Optional[str]
    ingredients_image_url: Optional[str]
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class DataExportRequest(BaseModel):
    include_profiles: bool = True
    include_scans: bool = True
    include_consumption: bool = True


class DataDeletionRequest(BaseModel):
    confirmation_code: str
    reason: Optional[str] = None


class HealthCheckResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
