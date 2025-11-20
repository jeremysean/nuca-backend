from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta
from app.database import get_db
from app.security.auth import get_current_user
from app.models import User, ScanSession, Product, Profile

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])

@router.get("/summary")
async def get_analytics_summary(
    period: str = Query(..., regex="^(week|month|year)$"),
    profile_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Calculate streak
    # Logic: Count consecutive days backwards from today where a scan session exists
    today = datetime.utcnow().date()
    streak_days = 0
    check_date = today
    
    while True:
        # Check if any scan exists for this date
        start_of_day = datetime.combine(check_date, datetime.min.time())
        end_of_day = datetime.combine(check_date, datetime.max.time())
        
        query = db.query(ScanSession).filter(
            ScanSession.user_id == current_user.id,
            ScanSession.scanned_at >= start_of_day,
            ScanSession.scanned_at <= end_of_day
        )
        
        if profile_id:
            query = query.filter(ScanSession.profile_id == profile_id)
            
        if query.first():
            streak_days += 1
            check_date -= timedelta(days=1)
        else:
            # If no scan today, check yesterday (maybe they haven't scanned TODAY yet but streak is still valid)
            if check_date == today:
                check_date -= timedelta(days=1)
                continue
            break
            
    return {
        "streak_days": streak_days,
        "period": period
    }

@router.get("/today")
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


@router.get("/history")
async def get_analytics_history(
    start_date: datetime,
    end_date: datetime,
    profile_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(ScanSession).filter(
        ScanSession.user_id == current_user.id,
        ScanSession.scanned_at >= start_date,
        ScanSession.scanned_at <= end_date,
        ScanSession.logged_as_consumed == True
    )
    
    if profile_id:
        query = query.filter(ScanSession.profile_id == profile_id)
    
    scans = query.all()
    
    # Group by day
    daily_data = {}
    # Initialize all days in range with 0
    delta = end_date - start_date
    for i in range(delta.days + 1):
        day = (start_date + timedelta(days=i)).date().isoformat()
        daily_data[day] = {
            'date': day,
            'sugar_pct': 0,
            'sodium_pct': 0,
            'satfat_pct': 0,
            'count': 0
        }

    for scan in scans:
        day = scan.scanned_at.date().isoformat()
        if day in daily_data:
            daily_data[day]['sugar_pct'] += float(scan.sugar_pct_of_limit) if scan.sugar_pct_of_limit else 0
            daily_data[day]['sodium_pct'] += float(scan.salt_pct_of_limit) if scan.salt_pct_of_limit else 0
            daily_data[day]['satfat_pct'] += float(scan.satfat_pct_of_limit) if scan.satfat_pct_of_limit else 0
            daily_data[day]['count'] += 1
    
    # Return as list sorted by date
    return sorted(daily_data.values(), key=lambda x: x['date'])
