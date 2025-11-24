from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from uuid import UUID
from datetime import datetime, timedelta
from typing import Optional
from app.database import get_db
from app.security.auth import get_current_user
from app.models import User, Profile, ScanSession
from app.schemas import AnalyticsSummaryResponse, AnalyticsHistoryResponse

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])

@router.get("/today")
async def get_today_analytics(
    profile_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    today = datetime.utcnow().date()
    
    query = db.query(ScanSession).filter(
        func.date(ScanSession.scanned_at) == today
    )
    
    if profile_id:
        query = query.filter(ScanSession.profile_id == profile_id)
    else:
        profile_ids = [p.id for p in current_user.profiles]
        query = query.filter(ScanSession.profile_id.in_(profile_ids))
    
    scans = query.all()
    
    return {
        "scans_today": len(scans),
        "calories_today": sum(s.consumed_kcal or 0 for s in scans),
        "sugar_g": sum(s.consumed_sugar_g or 0 for s in scans),
        "sodium_mg": sum(s.consumed_sodium_mg or 0 for s in scans),
    }

@router.get("/summary")
async def get_analytics_summary(
    period: str = Query("week", pattern="^(week|month)$"),
    profile_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    days = 7 if period == "week" else 30
    start_date = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(ScanSession).filter(
        ScanSession.scanned_at >= start_date
    )
    
    if profile_id:
        query = query.filter(ScanSession.profile_id == profile_id)
    else:
        profile_ids = [p.id for p in current_user.profiles]
        query = query.filter(ScanSession.profile_id.in_(profile_ids))
    
    scans = query.all()
    
    return {
        "total_scans": len(scans),
        "period": period,
        "start_date": start_date.isoformat(),
        "avg_daily_scans": len(scans) / days,
    }

@router.get("/history")
async def get_analytics_history(
    days: int = Query(7, ge=1, le=90),
    profile_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    start_date = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(ScanSession).filter(
        ScanSession.scanned_at >= start_date
    )
    
    if profile_id:
        query = query.filter(ScanSession.profile_id == profile_id)
    else:
        profile_ids = [p.id for p in current_user.profiles]
        query = query.filter(ScanSession.profile_id.in_(profile_ids))
    
    scans = query.order_by(desc(ScanSession.scanned_at)).all()
    
    daily_data = {}
    for scan in scans:
        date_key = scan.scanned_at.date().isoformat()
        if date_key not in daily_data:
            daily_data[date_key] = {
                "date": date_key,
                "scans": 0,
                "calories": 0,
                "sugar_g": 0,
                "sodium_mg": 0,
            }
        daily_data[date_key]["scans"] += 1
        daily_data[date_key]["calories"] += scan.consumed_kcal or 0
        daily_data[date_key]["sugar_g"] += scan.consumed_sugar_g or 0
        daily_data[date_key]["sodium_mg"] += scan.consumed_sodium_mg or 0
    
    return {"history": list(daily_data.values())}