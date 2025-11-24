from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from app.database import get_db
from app.security.auth import get_current_user
from app.models import User, Product, ProductNutrition
from app.schemas import ProductDetailResponse, ProductNutritionResponse

router = APIRouter(prefix="/api/v1/products", tags=["Products"])

@router.get("/{product_id}", response_model=ProductDetailResponse)
async def get_product(
    product_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    nutrition = db.query(ProductNutrition).filter(
        ProductNutrition.product_id == product.id
    ).first()
    
    return ProductDetailResponse(
        id=product.id,
        barcode=product.barcode,
        name=product.name,
        brand=product.brand,
        category=product.category,
        image_url=product.image_url,
        nutrition=ProductNutritionResponse(
            kcal_per_100=nutrition.kcal_per_100,
            protein_g=nutrition.protein_g,
            carbs_g=nutrition.carbs_g,
            sugar_g=nutrition.sugar_g,
            fat_g=nutrition.fat_g,
            saturated_fat_g=nutrition.saturated_fat_g,
            trans_fat_g=nutrition.trans_fat_g,
            fiber_g=nutrition.fiber_g,
            sodium_mg=nutrition.sodium_mg,
            serving_size_g=nutrition.serving_size_g,
        ) if nutrition else None,
        grade="C",
        grade_details=None,
    )

@router.get("/scan-result")
async def get_scan_result(
    barcode: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.barcode == barcode).first()
    if not product:
        return {"status": "not_found", "barcode": barcode}
    
    return {"status": "found", "product_id": str(product.id)}