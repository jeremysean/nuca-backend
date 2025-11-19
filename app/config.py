from pydantic_settings import BaseSettings
from typing import List
import secrets


class Settings(BaseSettings):
    environment: str = "development"
    
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    supabase_jwt_secret: str
    
    database_url: str
    
    openfoodfacts_api_url: str = "https://world.openfoodfacts.org/api/v2"
    
    cors_origins: List[str] = [
        "nuca://callback",
        "http://localhost:3000"]
    
    log_level: str = "INFO"
    
    encryption_key: str = secrets.token_urlsafe(32)
    
    data_retention_days: int = 730
    
    gdpr_enabled: bool = True
    ccpa_enabled: bool = True
    
    rate_limit_per_minute: int = 60
    
    session_timeout_minutes: int = 60
    refresh_token_expire_days: int = 30
    
    max_file_size_mb: int = 5
    allowed_image_types: List[str] = ["image/jpeg", "image/png", "image/webp"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
