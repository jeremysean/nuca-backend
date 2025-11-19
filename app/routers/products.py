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


@router.get("/scan/history")
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


@router.get("/analytics/today")
async def get_today_analytics(
    profile_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    query = db.query(ScanSession).filter(
        ScanSession.user_id == current_user.id,
        ScanSession.scanned_at >= today_start,
        ScanSession.logged_as_consumed == True
    )
    
    if profile_id:
        query = query.filter(ScanSession.profile_id == profile_id)
    
    scans = query.all()
    
    # Get profile limits
    limits = None
    if profile_id:
        profile = db.query(Profile).filter(Profile.id == profile_id).first()
        if profile:
            limits = {
                'sugar_hard': float(profile.daily_sugar_hard_g),
                'sodium_hard': float(profile.daily_sodium_hard_mg),
                'satfat_hard': float(profile.daily_satfat_hard_g)
            }
    
    # Calculate totals
    total_sugar_pct = sum(float(s.sugar_pct_of_limit) for s in scans if s.sugar_pct_of_limit)
    total_sodium_pct = sum(float(s.salt_pct_of_limit) for s in scans if s.salt_pct_of_limit)
    total_satfat_pct = sum(float(s.satfat_pct_of_limit) for s in scans if s.satfat_pct_of_limit)
    
    consumption_items = []
    for scan in scans:
        product = db.query(Product).filter(Product.id == scan.product_id).first()
        nutrition = product.nutrition if product else None
        
        if product:
            consumption_items.append({
                'product_id': str(product.id),
                'name': product.name,
                'brand': product.brand,
                'image_url': product.image_url,
                'grade': scan.grade.value if scan.grade else None,
                'consumed_at': scan.scanned_at.isoformat(),
                'sugar_g': float(nutrition.per_serving_sugars_g) if nutrition and nutrition.per_serving_sugars_g else 0,
                'sodium_mg': float(nutrition.per_serving_sodium_mg) if nutrition and nutrition.per_serving_sodium_mg else 0,
                'satfat_g': float(nutrition.per_serving_saturated_fat_g) if nutrition and nutrition.per_serving_saturated_fat_g else 0,
            })
    
    return {
        'date': datetime.utcnow().date().isoformat(),
        'profile_id': str(profile_id) if profile_id else None,
        'limits': limits,
        'consumed': {
            'sugar_pct': round(total_sugar_pct, 2),
            'sodium_pct': round(total_sodium_pct, 2),
            'satfat_pct': round(total_satfat_pct, 2)
        },
        'consumption_count': len(scans),
        'items': consumption_items
    }


@router.get("/analytics/week")
async def get_weekly_analytics(
    profile_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    week_start = datetime.utcnow() - timedelta(days=7)
    
    query = db.query(ScanSession).filter(
        ScanSession.user_id == current_user.id,
        ScanSession.scanned_at >= week_start,
        ScanSession.logged_as_consumed == True
    )
    
    if profile_id:
        query = query.filter(ScanSession.profile_id == profile_id)
    
    scans = query.all()
    
    # Group by day
    daily_data = {}
    for scan in scans:
        day = scan.scanned_at.date().isoformat()
        if day not in daily_data:
            daily_data[day] = {
                'sugar_pct': 0,
                'sodium_pct': 0,
                'satfat_pct': 0,
                'count': 0
            }
        
        daily_data[day]['sugar_pct'] += float(scan.sugar_pct_of_limit) if scan.sugar_pct_of_limit else 0
        daily_data[day]['sodium_pct'] += float(scan.salt_pct_of_limit) if scan.salt_pct_of_limit else 0
        daily_data[day]['satfat_pct'] += float(scan.satfat_pct_of_limit) if scan.satfat_pct_of_limit else 0
        daily_data[day]['count'] += 1
    
    return {
        'period': 'week',
        'profile_id': str(profile_id) if profile_id else None,
        'daily_data': daily_data,
        'total_scans': len(scans)
    }