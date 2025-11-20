from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta
from app.database import get_db
from app.security.auth import get_current_user
from app.models import User, ScanSession, Product, ProductNutrition, Profile, FamilyMember
from app.schemas import (
    ProductDetailResponse, ProductNutritionResponse, ProductIngredientResponse,
    ProductAllergenTagResponse, ProductGradingResult, AllergenResponse
)


router = APIRouter(prefix="/api/v1", tags=["Products & History"])


@router.get("/products/{product_id}", response_model=ProductDetailResponse)
async def get_product_by_id(
    product_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    nutrition = product.nutrition
    ingredients = product.ingredients
    allergen_tags = product.allergen_tags
    
    # Get the most recent scan session for this product to retrieve grading
    scan = db.query(ScanSession).filter(
        ScanSession.product_id == product_id,
        ScanSession.user_id == current_user.id
    ).order_by(desc(ScanSession.scanned_at)).first()
    
    grading_result = None
    if scan:
        allergen_matches = [
            ProductAllergenTagResponse(
                allergen=AllergenResponse.from_orm(tag.allergen),
                contain_type=tag.contain_type
            )
            for tag in allergen_tags
        ]
        
        warnings = []
        if scan.allergen_count > 0:
            warnings.append(f"Contains {scan.allergen_count} allergen(s) from your profile")
        if scan.dangerous_nutrients_count > 0:
            warnings.append(f"{scan.dangerous_nutrients_count} nutrient(s) in warning zone")
        
        grading_result = ProductGradingResult(
            grade=scan.grade,
            sugar_zone="red" if scan.sugar_pct_of_limit >= 75 else "orange" if scan.sugar_pct_of_limit >= 50 else "yellow" if scan.sugar_pct_of_limit >= 25 else "green",
            sodium_zone="red" if scan.salt_pct_of_limit >= 75 else "orange" if scan.salt_pct_of_limit >= 50 else "yellow" if scan.salt_pct_of_limit >= 25 else "green",
            satfat_zone="red" if scan.satfat_pct_of_limit >= 75 else "orange" if scan.satfat_pct_of_limit >= 50 else "yellow" if scan.satfat_pct_of_limit >= 25 else "green",
            dangerous_nutrients_count=scan.dangerous_nutrients_count,
            sugar_pct_of_limit=float(scan.sugar_pct_of_limit),
            sodium_pct_of_limit=float(scan.salt_pct_of_limit),
            satfat_pct_of_limit=float(scan.satfat_pct_of_limit),
            additive_count=scan.additive_count,
            nova_group=product.nova_group,
            allergen_matches=allergen_matches,
            warnings=warnings
        )
    
    return ProductDetailResponse(
        id=product.id,
        barcode=product.barcode,
        name=product.name,
        brand=product.brand,
        image_url=product.image_url,
        serving_size_label=product.serving_size_label,
        nova_group=product.nova_group,
        nutrition=ProductNutritionResponse.from_orm(nutrition) if nutrition else None,
        ingredients=[ProductIngredientResponse.from_orm(ing) for ing in ingredients],
        allergen_tags=[
            ProductAllergenTagResponse(
                allergen=AllergenResponse.from_orm(tag.allergen),
                contain_type=tag.contain_type
            )
            for tag in allergen_tags
        ],
        grading=grading_result
    )