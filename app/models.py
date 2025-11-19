from sqlalchemy import Column, String, Integer, Boolean, DECIMAL, Date, DateTime, Text, ForeignKey, Enum, JSON, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
# from sqlalchemy.orm import relationship
from sqlalchemy.orm import relationship as sa_relationship
import uuid
import enum


Base = declarative_base()


class SexEnum(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"


class ActivityLevelEnum(str, enum.Enum):
    sedentary = "sedentary"
    light = "light"
    active = "active"
    very_active = "very_active"


class GoalEnum(str, enum.Enum):
    reduce_sugar = "reduce_sugar"
    reduce_salt = "reduce_salt"
    reduce_ultra_processed = "reduce_ultra_processed"
    kids_snacks = "kids_snacks"
    general_health = "general_health"


class RelationshipEnum(str, enum.Enum):
    self = "self"
    child = "child"
    spouse = "spouse"
    parent = "parent"
    other = "other"


class ProductSourceEnum(str, enum.Enum):
    openfoodfacts = "openfoodfacts"
    user_suggested = "user_suggested"
    internal = "internal"


class ProductStatusEnum(str, enum.Enum):
    active = "active"
    pending_review = "pending_review"
    rejected = "rejected"


class GradeEnum(str, enum.Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class SeverityEnum(str, enum.Enum):
    mild = "mild"
    moderate = "moderate"
    severe = "severe"


class ContainTypeEnum(str, enum.Enum):
    contains = "contains"
    may_contain = "may_contain"
    free_from = "free_from"


class SuggestionStatusEnum(str, enum.Enum):
    pending = "pending"
    processed = "processed"
    rejected = "rejected"


class SubscriptionPlanEnum(str, enum.Enum):
    free = "free"
    premium = "premium"


class SubscriptionStatusEnum(str, enum.Enum):
    active = "active"
    canceled = "canceled"
    expired = "expired"


class ConsentTypeEnum(str, enum.Enum):
    health_data_processing = "health_data_processing"
    personalized_grading = "personalized_grading"
    family_data_processing = "family_data_processing"
    marketing = "marketing"
    analytics = "analytics"


class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supabase_user_id = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    display_name = Column(String(255))
    photo_url = Column(String(500))
    email_encrypted = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    data_retention_acknowledged = Column(Boolean, default=False)
    
    profiles = sa_relationship("Profile", back_populates="user", cascade="all, delete-orphan")
    family_members = sa_relationship("FamilyMember", back_populates="owner", cascade="all, delete-orphan")
    consents = sa_relationship("UserConsent", back_populates="user", cascade="all, delete-orphan")


class UserConsent(Base):
    __tablename__ = "user_consents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    consent_type = Column(Enum(ConsentTypeEnum), nullable=False)
    granted = Column(Boolean, default=False)
    granted_at = Column(DateTime(timezone=True))
    revoked_at = Column(DateTime(timezone=True))
    ip_address_hash = Column(String(64))
    user_agent_hash = Column(String(64))
    consent_version = Column(String(50), default="1.0")
    
    user = sa_relationship("User", back_populates="consents")
    
    __table_args__ = (
        Index("idx_user_consent_type", "user_id", "consent_type"),
    )


class Profile(Base):
    __tablename__ = "profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    date_of_birth_encrypted = Column(Text)
    sex = Column(Enum(SexEnum))
    height_cm_encrypted = Column(Text)
    weight_kg_encrypted = Column(Text)
    activity_level = Column(Enum(ActivityLevelEnum), default=ActivityLevelEnum.sedentary)
    
    has_hypertension_encrypted = Column(Text)
    has_diabetes_encrypted = Column(Text)
    has_heart_disease_encrypted = Column(Text)
    has_kidney_disease_encrypted = Column(Text)
    is_pregnant_encrypted = Column(Text)
    
    goal_primary = Column(Enum(GoalEnum))
    
    daily_eer_kcal = Column(DECIMAL(10, 2))
    daily_sugar_soft_g = Column(DECIMAL(10, 2))
    daily_sugar_hard_g = Column(DECIMAL(10, 2))
    daily_sodium_soft_mg = Column(DECIMAL(10, 2))
    daily_sodium_hard_mg = Column(DECIMAL(10, 2))
    daily_satfat_soft_g = Column(DECIMAL(10, 2))
    daily_satfat_hard_g = Column(DECIMAL(10, 2))
    daily_transfat_hard_g = Column(DECIMAL(10, 2))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = sa_relationship("User", back_populates="profiles")
    allergens = sa_relationship("ProfileAllergen", back_populates="profile", cascade="all, delete-orphan")
    scan_sessions = sa_relationship("ScanSession", back_populates="profile")


class FamilyMember(Base):
    __tablename__ = "family_members"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    relationship = Column(Enum(RelationshipEnum), nullable=False)
    date_of_birth_encrypted = Column(Text)
    sex = Column(Enum(SexEnum))
    height_cm_encrypted = Column(Text)
    weight_kg_encrypted = Column(Text)
    activity_level = Column(Enum(ActivityLevelEnum), default=ActivityLevelEnum.sedentary)
    health_flags_encrypted = Column(Text)
    is_default = Column(Boolean, default=False)
    
    daily_eer_kcal = Column(DECIMAL(10, 2))
    daily_sugar_soft_g = Column(DECIMAL(10, 2))
    daily_sugar_hard_g = Column(DECIMAL(10, 2))
    daily_sodium_soft_mg = Column(DECIMAL(10, 2))
    daily_sodium_hard_mg = Column(DECIMAL(10, 2))
    daily_satfat_soft_g = Column(DECIMAL(10, 2))
    daily_satfat_hard_g = Column(DECIMAL(10, 2))
    daily_transfat_hard_g = Column(DECIMAL(10, 2))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    owner = sa_relationship("User", back_populates="family_members")
    allergens = sa_relationship("FamilyMemberAllergen", back_populates="family_member", cascade="all, delete-orphan")
    scan_sessions = sa_relationship("ScanSession", back_populates="family_member")


class Allergen(Base):
    __tablename__ = "allergens"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)


class ProfileAllergen(Base):
    __tablename__ = "profile_allergens"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"))
    allergen_id = Column(UUID(as_uuid=True), ForeignKey("allergens.id", ondelete="CASCADE"), nullable=False)
    severity = Column(Enum(SeverityEnum), default=SeverityEnum.moderate)
    
    profile = sa_relationship("Profile", back_populates="allergens")
    allergen = sa_relationship("Allergen")


class FamilyMemberAllergen(Base):
    __tablename__ = "family_member_allergens"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    family_member_id = Column(UUID(as_uuid=True), ForeignKey("family_members.id", ondelete="CASCADE"))
    allergen_id = Column(UUID(as_uuid=True), ForeignKey("allergens.id", ondelete="CASCADE"), nullable=False)
    severity = Column(Enum(SeverityEnum), default=SeverityEnum.moderate)
    
    family_member = sa_relationship("FamilyMember", back_populates="allergens")
    allergen = sa_relationship("Allergen")


class Product(Base):
    __tablename__ = "products"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    barcode = Column(String(255), unique=True, index=True)
    name = Column(String(500), nullable=False)
    brand = Column(String(255))
    image_url = Column(String(500))
    serving_size_label = Column(String(100))
    nova_group = Column(Integer)
    source = Column(Enum(ProductSourceEnum), default=ProductSourceEnum.internal)
    status = Column(Enum(ProductStatusEnum), default=ProductStatusEnum.active)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    nutrition = sa_relationship("ProductNutrition", back_populates="product", uselist=False, cascade="all, delete-orphan")
    ingredients = sa_relationship("ProductIngredient", back_populates="product", cascade="all, delete-orphan")
    allergen_tags = sa_relationship("ProductAllergenTag", back_populates="product", cascade="all, delete-orphan")


class ProductNutrition(Base):
    __tablename__ = "product_nutritions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    per_100g_energy_kcal = Column(DECIMAL(10, 2))
    per_100g_fat_g = Column(DECIMAL(10, 2))
    per_100g_saturated_fat_g = Column(DECIMAL(10, 2))
    per_100g_carbs_g = Column(DECIMAL(10, 2))
    per_100g_sugars_g = Column(DECIMAL(10, 2))
    per_100g_protein_g = Column(DECIMAL(10, 2))
    per_100g_fiber_g = Column(DECIMAL(10, 2))
    per_100g_salt_g = Column(DECIMAL(10, 2))
    per_100g_sodium_mg = Column(DECIMAL(10, 2))
    
    per_serving_energy_kcal = Column(DECIMAL(10, 2))
    per_serving_sugars_g = Column(DECIMAL(10, 2))
    per_serving_sodium_mg = Column(DECIMAL(10, 2))
    per_serving_saturated_fat_g = Column(DECIMAL(10, 2))
    
    product = sa_relationship("Product", back_populates="nutrition")


class ProductIngredient(Base):
    __tablename__ = "product_ingredients"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    name_raw = Column(String(255), nullable=False)
    normalized_name = Column(String(255))
    is_additive = Column(Boolean, default=False)
    additive_code = Column(String(50))
    
    product = sa_relationship("Product", back_populates="ingredients")


class ProductAllergenTag(Base):
    __tablename__ = "product_allergen_tags"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    allergen_id = Column(UUID(as_uuid=True), ForeignKey("allergens.id", ondelete="CASCADE"), nullable=False)
    contain_type = Column(Enum(ContainTypeEnum), nullable=False)
    
    product = sa_relationship("Product", back_populates="allergen_tags")
    allergen = sa_relationship("Allergen")


class IngredientKnowledgebase(Base):
    __tablename__ = "ingredient_knowledgebase"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    normalized_name = Column(String(255), unique=True, nullable=False, index=True)
    category = Column(String(100))
    short_description = Column(Text)
    risk_note = Column(Text)
    child_caution = Column(Boolean, default=False)


class ScanSession(Base):
    __tablename__ = "scan_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"))
    family_member_id = Column(UUID(as_uuid=True), ForeignKey("family_members.id", ondelete="SET NULL"))
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    scanned_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    grade = Column(Enum(GradeEnum))
    dangerous_nutrients_count = Column(Integer, default=0)
    allergen_count = Column(Integer, default=0)
    sugar_pct_of_limit = Column(DECIMAL(10, 2))
    salt_pct_of_limit = Column(DECIMAL(10, 2))
    satfat_pct_of_limit = Column(DECIMAL(10, 2))
    additive_count = Column(Integer, default=0)
    logged_as_consumed = Column(Boolean, default=False)
    
    profile = sa_relationship("Profile", back_populates="scan_sessions")
    family_member = sa_relationship("FamilyMember", back_populates="scan_sessions")
    consumption_log = sa_relationship("ConsumptionLog", back_populates="scan_session", uselist=False)
    
    __table_args__ = (
        Index("idx_scan_user_date", "user_id", "scanned_at"),
    )


class ConsumptionLog(Base):
    __tablename__ = "consumption_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_session_id = Column(UUID(as_uuid=True), ForeignKey("scan_sessions.id", ondelete="CASCADE"), nullable=False, unique=True)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"))
    family_member_id = Column(UUID(as_uuid=True), ForeignKey("family_members.id", ondelete="SET NULL"))
    serving_multiplier = Column(DECIMAL(5, 2), default=1.0)
    consumed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    scan_session = sa_relationship("ScanSession", back_populates="consumption_log")


class ProductSuggestion(Base):
    __tablename__ = "product_suggestions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    barcode = Column(String(255))
    front_image_url = Column(String(500))
    nutrition_label_image_url = Column(String(500))
    ingredients_image_url = Column(String(500))
    status = Column(Enum(SuggestionStatusEnum), default=SuggestionStatusEnum.pending)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    processed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(50))
    plan = Column(Enum(SubscriptionPlanEnum), default=SubscriptionPlanEnum.free)
    status = Column(Enum(SubscriptionStatusEnum), default=SubscriptionStatusEnum.active)
    expires_at = Column(DateTime(timezone=True))
    raw_receipt = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ProductAffiliateLink(Base):
    __tablename__ = "product_affiliate_links"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    partner = Column(String(100), nullable=False)
    url = Column(String(1000), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100))
    resource_id = Column(UUID(as_uuid=True))
    ip_address_hash = Column(String(64))
    user_agent_hash = Column(String(64))
    metadata_json = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    __table_args__ = (
        Index("idx_audit_user_action", "user_id", "action", "created_at"),
    )


class DataDeletionRequest(Base):
    __tablename__ = "data_deletion_requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    scheduled_deletion_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True))
    status = Column(String(50), default="pending")
