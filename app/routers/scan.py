from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
from datetime import datetime
import httpx
from app.database import get_db
from app.security.auth import get_current_user, AuthService
from app.security.encryption import decrypt_profile_health_data
from app.models import (
    User, Profile, FamilyMember, Product, ProductNutrition, ProductIngredient,
    ProductAllergenTag, ScanSession, ConsentTypeEnum, AuditLog
)
from app.schemas import (
    ScanBarcodeRequest, ScanBarcodeResponse, ProductDetailResponse,
    ProductNutritionResponse, ProductIngredientResponse, ProductAllergenTagResponse,
    ProductGradingResult, AllergenResponse
)
from app.services.grading_engine import ProductGradingEngine
from app.config import settings


router = APIRouter(prefix="/api/v1/scan", tags=["Scanning"])


async def fetch_from_openfoodfacts(barcode: str) -> Optional[dict]:
    url = f"{settings.openfoodfacts_api_url}/product/{barcode}.json"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == 1:
                    return data.get("product")
    except Exception as e:
        print(f"OpenFoodFacts API error: {e}")
    
    return None


def create_product_from_openfoodfacts(product_data: dict, barcode: str, db: Session) -> Product:
    product = Product(
        barcode=barcode,
        name=product_data.get("product_name", "Unknown Product"),
        brand=product_data.get("brands", ""),
        image_url=product_data.get("image_url"),
        serving_size_label=product_data.get("serving_size"),
        nova_group=product_data.get("nova_group"),
        source="openfoodfacts",
        status="active"
    )
    
    db.add(product)
    db.flush()
    
    nutriments = product_data.get("nutriments", {})
    
    nutrition = ProductNutrition(
        product_id=product.id,
        per_100g_energy_kcal=nutriments.get("energy-kcal_100g"),
        per_100g_fat_g=nutriments.get("fat_100g"),
        per_100g_saturated_fat_g=nutriments.get("saturated-fat_100g"),
        per_100g_carbs_g=nutriments.get("carbohydrates_100g"),
        per_100g_sugars_g=nutriments.get("sugars_100g"),
        per_100g_protein_g=nutriments.get("proteins_100g"),
        per_100g_fiber_g=nutriments.get("fiber_100g"),
        per_100g_salt_g=nutriments.get("salt_100g"),
        per_100g_sodium_mg=nutriments.get("sodium_100g") * 1000 if nutriments.get("sodium_100g") else None,
        per_serving_energy_kcal=nutriments.get("energy-kcal_serving"),
        per_serving_sugars_g=nutriments.get("sugars_serving"),
        per_serving_sodium_mg=nutriments.get("sodium_serving") * 1000 if nutriments.get("sodium_serving") else None,
        per_serving_saturated_fat_g=nutriments.get("saturated-fat_serving")
    )
    
    db.add(nutrition)
    
    ingredients_text = product_data.get("ingredients_text", "")
    if ingredients_text:
        for ing in ingredients_text.split(",")[:20]:
            ingredient = ProductIngredient(
                product_id=product.id,
                name_raw=ing.strip(),
                normalized_name=ing.strip().lower(),
                is_additive=False
            )
            db.add(ingredient)
    
    db.commit()
    db.refresh(product)
    
    return product


@router.post("/barcode", response_model=ScanBarcodeResponse)
async def scan_barcode(
    scan_data: ScanBarcodeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    AuthService.require_consent(
        str(current_user.id),
        ConsentTypeEnum.personalized_grading,
        db
    )
    
    profile_or_member = None
    limits = None
    profile_allergens = []
    
    if scan_data.profile_id:
        profile_or_member = db.query(Profile).filter(
            Profile.id == scan_data.profile_id,
            Profile.user_id == current_user.id
        ).first()
        
        if not profile_or_member:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        limits = {
            "sugar_soft": float(profile_or_member.daily_sugar_soft_g),
            "sugar_hard": float(profile_or_member.daily_sugar_hard_g),
            "sodium_soft": float(profile_or_member.daily_sodium_soft_mg),
            "sodium_hard": float(profile_or_member.daily_sodium_hard_mg),
            "satfat_soft": float(profile_or_member.daily_satfat_soft_g),
            "satfat_hard": float(profile_or_member.daily_satfat_hard_g)
        }
        
        profile_allergens = [pa.allergen for pa in profile_or_member.allergens]
    
    elif scan_data.family_member_id:
        profile_or_member = db.query(FamilyMember).filter(
            FamilyMember.id == scan_data.family_member_id,
            FamilyMember.owner_user_id == current_user.id
        ).first()
        
        if not profile_or_member:
            raise HTTPException(status_code=404, detail="Family member not found")
        
        limits = {
            "sugar_soft": float(profile_or_member.daily_sugar_soft_g),
            "sugar_hard": float(profile_or_member.daily_sugar_hard_g),
            "sodium_soft": float(profile_or_member.daily_sodium_soft_mg),
            "sodium_hard": float(profile_or_member.daily_sodium_hard_mg),
            "satfat_soft": float(profile_or_member.daily_satfat_soft_g),
            "satfat_hard": float(profile_or_member.daily_satfat_hard_g)
        }
        
        profile_allergens = [pa.allergen for pa in profile_or_member.allergens]
    
    else:
        raise HTTPException(status_code=400, detail="Either profile_id or family_member_id required")
    
    product = db.query(Product).filter(Product.barcode == scan_data.barcode).first()
    
    if not product:
        off_data = await fetch_from_openfoodfacts(scan_data.barcode)
        
        if off_data:
            product = create_product_from_openfoodfacts(off_data, scan_data.barcode, db)
        else:
            return ScanBarcodeResponse(
                status="not_found",
                product=None,
                suggest_add=True,
                message="Product not found. You can suggest adding it."
            )
    
    nutrition = product.nutrition
    ingredients = product.ingredients
    allergen_tags = product.allergen_tags
    
    allergen_matches = []
    for tag in allergen_tags:
        if tag.allergen in profile_allergens and tag.contain_type in ["contains", "may_contain"]:
            allergen_matches.append(ProductAllergenTagResponse(
                allergen=AllergenResponse(
                    id=tag.allergen.id,
                    code=tag.allergen.code,
                    name=tag.allergen.name,
                    description=tag.allergen.description
                ),
                contain_type=tag.contain_type
            ))
    
    grading_result = None
    if nutrition and limits:
        additive_count = sum(1 for ing in ingredients if ing.is_additive)
        
        grading = ProductGradingEngine.grade_product(
            sugar_per_serving=float(nutrition.per_serving_sugars_g) if nutrition.per_serving_sugars_g else None,
            sodium_per_serving=float(nutrition.per_serving_sodium_mg) if nutrition.per_serving_sodium_mg else None,
            satfat_per_serving=float(nutrition.per_serving_saturated_fat_g) if nutrition.per_serving_saturated_fat_g else None,
            sugar_soft_limit=limits["sugar_soft"],
            sugar_hard_limit=limits["sugar_hard"],
            sodium_soft_limit=limits["sodium_soft"],
            sodium_hard_limit=limits["sodium_hard"],
            satfat_soft_limit=limits["satfat_soft"],
            satfat_hard_limit=limits["satfat_hard"],
            additive_count=additive_count,
            nova_group=product.nova_group
        )
        
        warnings = []
        if allergen_matches:
            warnings.append(f"Contains {len(allergen_matches)} allergen(s) from your profile")
        if grading["dangerous_nutrients_count"] > 0:
            warnings.append(f"{grading['dangerous_nutrients_count']} nutrient(s) in warning zone")
        
        grading_result = ProductGradingResult(
            grade=grading["grade"],
            sugar_zone=grading["sugar_zone"],
            sodium_zone=grading["sodium_zone"],
            satfat_zone=grading["satfat_zone"],
            dangerous_nutrients_count=grading["dangerous_nutrients_count"],
            sugar_pct_of_limit=grading["sugar_pct_of_limit"],
            sodium_pct_of_limit=grading["sodium_pct_of_limit"],
            satfat_pct_of_limit=grading["satfat_pct_of_limit"],
            additive_count=grading["additive_count"],
            nova_group=grading["nova_group"],
            allergen_matches=allergen_matches,
            warnings=warnings
        )
        
        scan_session = ScanSession(
            user_id=current_user.id,
            profile_id=scan_data.profile_id,
            family_member_id=scan_data.family_member_id,
            product_id=product.id,
            grade=grading["grade"],
            dangerous_nutrients_count=grading["dangerous_nutrients_count"],
            allergen_count=len(allergen_matches),
            sugar_pct_of_limit=grading["sugar_pct_of_limit"],
            salt_pct_of_limit=grading["sodium_pct_of_limit"],
            satfat_pct_of_limit=grading["satfat_pct_of_limit"],
            additive_count=grading["additive_count"]
        )
        
        db.add(scan_session)
        db.commit()
    
    product_response = ProductDetailResponse(
        id=product.id,
        barcode=product.barcode,
        name=product.name,
        brand=product.brand,
        image_url=product.image_url,
        serving_size_label=product.serving_size_label,
        nova_group=product.nova_group,
        nutrition=ProductNutritionResponse.from_orm(nutrition) if nutrition else None,
        ingredients=[ProductIngredientResponse.from_orm(ing) for ing in ingredients],
        allergen_tags=[ProductAllergenTagResponse(
            allergen=AllergenResponse.from_orm(tag.allergen),
            contain_type=tag.contain_type
        ) for tag in allergen_tags],
        grading=grading_result
    )
    
    return ScanBarcodeResponse(
        status="success",
        product=product_response,
        suggest_add=False
    )


@router.get("/history")
async def get_scan_history(
    profile_id: Optional[UUID] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(ScanSession).filter(
        ScanSession.user_id == current_user.id
    )
    
    if profile_id:
        query = query.filter(ScanSession.profile_id == profile_id)
    
    total = query.count()
    
    scans = query.order_by(desc(ScanSession.scanned_at)).offset(offset).limit(limit).all()
    
    results = []
    for scan in scans:
        product = scan.product if hasattr(scan, 'product') else db.query(Product).filter(Product.id == scan.product_id).first()
        
        if product:
            results.append({
                'id': str(scan.id),
                'product_id': str(product.id),
                'barcode': product.barcode,
                'name': product.name,
                'brand': product.brand,
                'image_url': product.image_url,
                'grade': scan.grade.value if scan.grade else None,
                'scanned_at': scan.scanned_at.isoformat(),
                'dangerous_nutrients_count': scan.dangerous_nutrients_count,
                'allergen_count': scan.allergen_count,
                'sugar_pct_of_limit': float(scan.sugar_pct_of_limit) if scan.sugar_pct_of_limit else 0,
                'logged_as_consumed': scan.logged_as_consumed
            })
    
    return {
        'total': total,
        'limit': limit,
        'offset': offset,
        'results': results
    }
