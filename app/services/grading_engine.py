from typing import Optional, Dict
from app.models import GradeEnum


class NutrientZone:
    GREEN = "green"
    YELLOW = "yellow"
    ORANGE = "orange"
    RED = "red"


class ProductGradingEngine:
    
    @staticmethod
    def calculate_nutrient_zone(
        value_per_serving: float,
        soft_limit: float,
        hard_limit: float
    ) -> str:
        if value_per_serving is None:
            return NutrientZone.GREEN
        
        pct_of_hard = (value_per_serving / hard_limit) * 100 if hard_limit > 0 else 0
        pct_of_soft = (value_per_serving / soft_limit) * 100 if soft_limit > 0 else 0
        
        if pct_of_soft < 25:
            return NutrientZone.GREEN
        elif pct_of_hard < 50:
            return NutrientZone.YELLOW
        elif pct_of_hard < 75:
            return NutrientZone.ORANGE
        else:
            return NutrientZone.RED
    
    @staticmethod
    def calculate_grade(
        sugar_zone: str,
        sodium_zone: str,
        satfat_zone: str,
        additive_count: int,
        nova_group: Optional[int],
        fiber_g: Optional[float],
        protein_g: Optional[float]
    ) -> str:
        zones = [sugar_zone, sodium_zone, satfat_zone]
        
        red_count = zones.count(NutrientZone.RED)
        orange_count = zones.count(NutrientZone.ORANGE)
        
        is_ultra_processed = nova_group == 4
        high_additive = additive_count >= 5
        
        if red_count >= 2:
            return GradeEnum.D
        
        if red_count >= 1 and (is_ultra_processed or high_additive):
            return GradeEnum.D
        
        if red_count >= 1 or orange_count >= 2:
            return GradeEnum.C
        
        if orange_count >= 1:
            return GradeEnum.B
        
        if is_ultra_processed and additive_count >= 3:
            return GradeEnum.B
        
        return GradeEnum.A
    
    @staticmethod
    def grade_product(
        sugar_per_serving: Optional[float],
        sodium_per_serving: Optional[float],
        satfat_per_serving: Optional[float],
        sugar_soft_limit: float,
        sugar_hard_limit: float,
        sodium_soft_limit: float,
        sodium_hard_limit: float,
        satfat_soft_limit: float,
        satfat_hard_limit: float,
        additive_count: int,
        nova_group: Optional[int],
        fiber_per_serving: Optional[float] = None,
        protein_per_serving: Optional[float] = None
    ) -> Dict:
        
        sugar_zone = ProductGradingEngine.calculate_nutrient_zone(
            sugar_per_serving, sugar_soft_limit, sugar_hard_limit
        )
        sodium_zone = ProductGradingEngine.calculate_nutrient_zone(
            sodium_per_serving, sodium_soft_limit, sodium_hard_limit
        )
        satfat_zone = ProductGradingEngine.calculate_nutrient_zone(
            satfat_per_serving, satfat_soft_limit, satfat_hard_limit
        )
        
        grade = ProductGradingEngine.calculate_grade(
            sugar_zone,
            sodium_zone,
            satfat_zone,
            additive_count,
            nova_group,
            fiber_per_serving,
            protein_per_serving
        )
        
        dangerous_nutrients = sum([
            1 for zone in [sugar_zone, sodium_zone, satfat_zone]
            if zone in [NutrientZone.ORANGE, NutrientZone.RED]
        ])
        
        sugar_pct = (sugar_per_serving / sugar_hard_limit * 100) if sugar_per_serving and sugar_hard_limit else 0
        sodium_pct = (sodium_per_serving / sodium_hard_limit * 100) if sodium_per_serving and sodium_hard_limit else 0
        satfat_pct = (satfat_per_serving / satfat_hard_limit * 100) if satfat_per_serving and satfat_hard_limit else 0
        
        return {
            "grade": grade,
            "sugar_zone": sugar_zone,
            "sodium_zone": sodium_zone,
            "satfat_zone": satfat_zone,
            "dangerous_nutrients_count": dangerous_nutrients,
            "sugar_pct_of_limit": round(sugar_pct, 2),
            "sodium_pct_of_limit": round(sodium_pct, 2),
            "satfat_pct_of_limit": round(satfat_pct, 2),
            "additive_count": additive_count,
            "nova_group": nova_group
        }
