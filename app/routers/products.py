from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional
from app.database import get_db
from app.security.auth import get_current_user
from app.models import (
    User, Product, ProductNutrition, ProductIngredient, 
    ProductAllergenTag, Profile, FamilyMember
)
from app.services.grading_engine import ProductGradingEngine

router = APIRouter(prefix="/api/v1/products", tags=["Products"])


@router.get("/{product_id}")
async def get_product(
    product_id: UUID,
    profile_id: Optional[UUID] = Query(None),
    family_member_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get product details with optional personalized grading"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    nutrition = product.nutrition
    ingredients = product.ingredients
    allergen_tags = product.allergen_tags
    
    # Build nutrition response
    nutrition_response = None
    if nutrition:
        nutrition_response = {
            "per_100g_energy_kcal": float(nutrition.per_100g_energy_kcal) if nutrition.per_100g_energy_kcal else None,
            "per_100g_fat_g": float(nutrition.per_100g_fat_g) if nutrition.per_100g_fat_g else None,
            "per_100g_saturated_fat_g": float(nutrition.per_100g_saturated_fat_g) if nutrition.per_100g_saturated_fat_g else None,
            "per_100g_carbs_g": float(nutrition.per_100g_carbs_g) if nutrition.per_100g_carbs_g else None,
            "per_100g_sugars_g": float(nutrition.per_100g_sugars_g) if nutrition.per_100g_sugars_g else None,
            "per_100g_protein_g": float(nutrition.per_100g_protein_g) if nutrition.per_100g_protein_g else None,
            "per_100g_fiber_g": float(nutrition.per_100g_fiber_g) if nutrition.per_100g_fiber_g else None,
            "per_100g_sodium_mg": float(nutrition.per_100g_sodium_mg) if nutrition.per_100g_sodium_mg else None,
            "per_serving_energy_kcal": float(nutrition.per_serving_energy_kcal) if nutrition.per_serving_energy_kcal else None,
            "per_serving_sugars_g": float(nutrition.per_serving_sugars_g) if nutrition.per_serving_sugars_g else None,
            "per_serving_sodium_mg": float(nutrition.per_serving_sodium_mg) if nutrition.per_serving_sodium_mg else None,
            "per_serving_saturated_fat_g": float(nutrition.per_serving_saturated_fat_g) if nutrition.per_serving_saturated_fat_g else None,
        }
    
    # Build ingredients response
    ingredients_response = [
        {
            "name_raw": ing.name_raw,
            "is_additive": ing.is_additive,
            "additive_code": ing.additive_code,
        }
        for ing in ingredients
    ]
    
    # Build allergen tags response
    allergen_tags_response = [
        {
            "allergen": {
                "id": str(tag.allergen.id),
                "code": tag.allergen.code,
                "name": tag.allergen.name,
                "description": tag.allergen.description,
            },
            "contain_type": tag.contain_type.value if hasattr(tag.contain_type, 'value') else tag.contain_type,
        }
        for tag in allergen_tags
    ]
    
    # Calculate grading if profile provided
    grading_result = None
    limits = None
    
    if profile_id:
        profile = db.query(Profile).filter(
            Profile.id == profile_id,
            Profile.user_id == current_user.id
        ).first()
        if profile and profile.daily_sugar_hard_g:
            limits = {
                "sugar_soft": float(profile.daily_sugar_soft_g),
                "sugar_hard": float(profile.daily_sugar_hard_g),
                "sodium_soft": float(profile.daily_sodium_soft_mg),
                "sodium_hard": float(profile.daily_sodium_hard_mg),
                "satfat_soft": float(profile.daily_satfat_soft_g),
                "satfat_hard": float(profile.daily_satfat_hard_g),
            }
    elif family_member_id:
        member = db.query(FamilyMember).filter(
            FamilyMember.id == family_member_id,
            FamilyMember.owner_user_id == current_user.id
        ).first()
        if member and member.daily_sugar_hard_g:
            limits = {
                "sugar_soft": float(member.daily_sugar_soft_g),
                "sugar_hard": float(member.daily_sugar_hard_g),
                "sodium_soft": float(member.daily_sodium_soft_mg),
                "sodium_hard": float(member.daily_sodium_hard_mg),
                "satfat_soft": float(member.daily_satfat_soft_g),
                "satfat_hard": float(member.daily_satfat_hard_g),
            }
    
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
        
        grading_result = {
            "grade": grading["grade"].value if hasattr(grading["grade"], 'value') else grading["grade"],
            "sugar_zone": grading["sugar_zone"],
            "sodium_zone": grading["sodium_zone"],
            "satfat_zone": grading["satfat_zone"],
            "dangerous_nutrients_count": grading["dangerous_nutrients_count"],
            "sugar_pct_of_limit": grading["sugar_pct_of_limit"],
            "sodium_pct_of_limit": grading["sodium_pct_of_limit"],
            "satfat_pct_of_limit": grading["satfat_pct_of_limit"],
            "additive_count": grading["additive_count"],
            "nova_group": grading["nova_group"],
            "allergen_matches": [],
            "warnings": [],
        }
    
    return {
        "id": str(product.id),
        "barcode": product.barcode,
        "name": product.name,
        "brand": product.brand,
        "image_url": product.image_url,
        "serving_size_label": product.serving_size_label,
        "nova_group": product.nova_group,
        "nutrition": nutrition_response,
        "ingredients": ingredients_response,
        "allergen_tags": allergen_tags_response,
        "grading": grading_result,
    }


@router.get("/by-barcode/{barcode}")
async def get_product_by_barcode(
    barcode: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if product exists by barcode"""
    product = db.query(Product).filter(Product.barcode == barcode).first()
    if not product:
        return {"status": "not_found", "barcode": barcode}
    
    return {"status": "found", "product_id": str(product.id)}