from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
import logging
from app.config import settings
from app.routers import consent, profiles, family, scan
from app.schemas import HealthCheckResponse
from app.routers import consent, profiles, family, scan, auth, products


logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="NUCA - Nutrition Care API",
    description="Personalized nutrition scanning and tracking with health data protection compliance",
    version="1.0.0",
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url="/redoc" if settings.environment == "development" else None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"]
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.utcnow()
    
    response = await call_next(request)
    
    duration = (datetime.utcnow() - start_time).total_seconds()
    
    logger.info(
        f"{request.method} {request.url.path} - Status: {response.status_code} - Duration: {duration:.3f}s"
    )
    
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error occurred",
            "type": "internal_error"
        }
    )


app.include_router(consent.router)
app.include_router(profiles.router)
app.include_router(family.router)
app.include_router(scan.router)
app.include_router(auth.router)

@app.get("/healthz", response_model=HealthCheckResponse)
async def health_check():
    return HealthCheckResponse(
        status="ok",
        timestamp=datetime.utcnow(),
        version="1.0.0"
    )


@app.get("/")
async def root():
    return {
        "service": "NUCA Nutrition Care API",
        "version": "1.0.0",
        "status": "running",
        "documentation": "/docs" if settings.environment == "development" else "Contact administrator",
        "privacy_notice": "This service processes sensitive health data. All data is encrypted at rest and in transit. Users have full control over their data including export and deletion rights under GDPR/CCPA.",
        "disclaimer": "NUCA is a nutrition information and wellness tool, not a medical device. It does not provide medical advice, diagnosis, or treatment. Consult healthcare professionals for medical decisions."
    }


@app.get("/api/v1/privacy-policy")
async def privacy_policy():
    return {
        "version": "1.0",
        "effective_date": "2025-01-01",
        "data_controller": "NUCA Nutrition Care",
        "summary": "NUCA processes your health data (health conditions, measurements) with your explicit consent to provide personalized nutrition recommendations.",
        "data_collected": [
            "Profile information (name, date of birth, sex, height, weight, activity level)",
            "Health conditions (encrypted: hypertension, diabetes, heart disease, kidney disease, pregnancy status)",
            "Allergen information",
            "Product scan history",
            "Consumption logs"
        ],
        "data_usage": [
            "Calculate personalized daily nutrient limits",
            "Grade scanned products (A-D)",
            "Track daily nutrient consumption",
            "Identify allergens in products",
            "Improve service quality"
        ],
        "data_protection": [
            "All sensitive health data encrypted at rest using AES-256",
            "HTTPS/TLS encryption for data in transit",
            "Access controls and authentication",
            "Regular security audits",
            "No third-party sharing without consent"
        ],
        "user_rights": [
            "Right to access your data (export feature)",
            "Right to rectification (edit profiles)",
            "Right to erasure (delete account)",
            "Right to data portability (JSON export)",
            "Right to withdraw consent anytime",
            "Right to object to processing"
        ],
        "data_retention": f"{settings.data_retention_days} days from last activity, then automatic deletion",
        "contact": "privacy@nuca.care"
    }


@app.get("/api/v1/terms-of-service")
async def terms_of_service():
    return {
        "version": "1.0",
        "effective_date": "2025-01-01",
        "service_description": "NUCA provides nutrition information scanning and personalized grading for packaged food and beverages.",
        "disclaimer": [
            "NUCA is NOT a medical device",
            "NUCA does NOT provide medical advice, diagnosis, or treatment",
            "NUCA recommendations are informational only",
            "Always consult qualified healthcare professionals for medical decisions",
            "NUCA does not replace professional dietary advice",
            "Product nutrition data sourced from OpenFoodFacts and user contributions may contain errors"
        ],
        "user_responsibilities": [
            "Provide accurate health information",
            "Verify product information before consumption",
            "Do not rely solely on NUCA for medical decisions",
            "Keep account credentials secure",
            "Review allergen warnings carefully"
        ],
        "consent_requirements": [
            "Health data processing consent required for personalized features",
            "Family data processing consent required for family member profiles",
            "Consents can be withdrawn anytime in app settings"
        ],
        "limitations": [
            "Grading based on general nutrition guidelines, not personal medical needs",
            "Product database may be incomplete",
            "OCR scanning may have errors",
            "Service availability not guaranteed"
        ],
        "contact": "support@nuca.care"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development"
    )
