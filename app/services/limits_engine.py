from dataclasses import dataclass
from datetime import date
from typing import Optional
import math


@dataclass
class PersonalLimits:
    eer_kcal: float
    sugar_soft_g: float
    sugar_hard_g: float
    sodium_soft_mg: float
    sodium_hard_mg: float
    satfat_soft_g: float
    satfat_hard_g: float
    transfat_hard_g: float
    flags: dict


class PersonalLimitsEngine:
    KCAL_PER_G_CARB = 4.0
    KCAL_PER_G_FAT = 9.0
    BASE_SODIUM_HARD_MG = 2000
    BASE_SODIUM_SOFT_MG = 1500
    
    PA_COEFFICIENTS = {
        "male": {
            "sedentary": 1.00,
            "light": 1.11,
            "active": 1.25,
            "very_active": 1.48
        },
        "female": {
            "sedentary": 1.00,
            "light": 1.12,
            "active": 1.27,
            "very_active": 1.45
        }
    }
    
    @staticmethod
    def calculate_age(date_of_birth: date) -> int:
        today = date.today()
        days = (today - date_of_birth).days
        return int(days / 365.25)
    
    @staticmethod
    def get_default_height(age_years: int, sex: str) -> float:
        if age_years >= 18:
            return 165 if sex == "male" else 158
        elif age_years >= 14:
            return 160 if sex == "male" else 155
        else:
            return 140
    
    @staticmethod
    def get_default_weight(age_years: int, sex: str) -> float:
        if age_years >= 18:
            return 65 if sex == "male" else 55
        elif age_years >= 14:
            return 58 if sex == "male" else 52
        else:
            return 35
    
    @staticmethod
    def compute_eer_adult(
        age_years: int,
        sex: str,
        height_m: float,
        weight_kg: float,
        pa: float
    ) -> float:
        if sex == "male":
            return 662 - 9.53 * age_years + pa * (15.91 * weight_kg + 539.6 * height_m)
        else:
            return 354 - 6.91 * age_years + pa * (9.36 * weight_kg + 726 * height_m)
    
    @staticmethod
    def compute_eer_child(age_years: int, sex: str, activity_level: str) -> float:
        if 3 <= age_years <= 8:
            if sex == "male":
                return 1400 if activity_level in ["active", "very_active"] else 1200
            else:
                return 1300 if activity_level in ["active", "very_active"] else 1100
        elif 9 <= age_years <= 13:
            if sex == "male":
                return 1800 if activity_level in ["active", "very_active"] else 1600
            else:
                return 1700 if activity_level in ["active", "very_active"] else 1500
        else:
            return 1400
    
    @staticmethod
    def compute_personal_limits(
        date_of_birth: date,
        sex: str,
        height_cm: Optional[float],
        weight_kg: Optional[float],
        activity_level: str,
        has_hypertension: bool = False,
        has_diabetes: bool = False,
        has_heart_disease: bool = False,
        has_kidney_disease: bool = False,
        is_pregnant: bool = False
    ) -> PersonalLimits:
        
        age_years = PersonalLimitsEngine.calculate_age(date_of_birth)
        
        if height_cm is None:
            height_cm = PersonalLimitsEngine.get_default_height(age_years, sex)
        if weight_kg is None:
            weight_kg = PersonalLimitsEngine.get_default_weight(age_years, sex)
        
        height_m = height_cm / 100.0
        bmi = weight_kg / (height_m ** 2)
        
        is_child = age_years < 18
        risk_glucose = has_diabetes or bmi >= 30
        risk_cvd = has_heart_disease or has_diabetes
        risk_hypertension = has_hypertension or has_kidney_disease
        risk_pregnancy = is_pregnant
        
        if is_child and age_years < 14:
            eer = PersonalLimitsEngine.compute_eer_child(age_years, sex, activity_level)
        else:
            pa = PersonalLimitsEngine.PA_COEFFICIENTS.get(sex, {}).get(activity_level, 1.0)
            eer = PersonalLimitsEngine.compute_eer_adult(age_years, sex, height_m, weight_kg, pa)
        
        if risk_pregnancy:
            eer += 340
        
        eer = max(1000, min(eer, 3500))
        
        if risk_glucose:
            sugar_pct_hard = 0.05
            sugar_pct_soft = 0.05
        else:
            sugar_pct_hard = 0.10
            sugar_pct_soft = 0.075
        
        sugar_hard = eer * sugar_pct_hard / PersonalLimitsEngine.KCAL_PER_G_CARB
        sugar_soft = eer * sugar_pct_soft / PersonalLimitsEngine.KCAL_PER_G_CARB
        
        if is_child:
            factor = max(0.5, min(eer / 2000.0, 1.0))
            base_hard = PersonalLimitsEngine.BASE_SODIUM_HARD_MG * factor
            base_soft = PersonalLimitsEngine.BASE_SODIUM_SOFT_MG * factor
        else:
            base_hard = PersonalLimitsEngine.BASE_SODIUM_HARD_MG
            base_soft = PersonalLimitsEngine.BASE_SODIUM_SOFT_MG
        
        if risk_hypertension or risk_cvd:
            if not is_child:
                sodium_hard = 1500.0
                sodium_soft = 1200.0
            else:
                sodium_hard = base_hard * 0.75
                sodium_soft = base_soft * 0.75
        else:
            sodium_hard = base_hard
            sodium_soft = base_soft
        
        if risk_cvd or risk_glucose:
            sat_pct_hard = 0.07
            sat_pct_soft = 0.06
        else:
            sat_pct_hard = 0.10
            sat_pct_soft = 0.08
        
        sat_hard = eer * sat_pct_hard / PersonalLimitsEngine.KCAL_PER_G_FAT
        sat_soft = eer * sat_pct_soft / PersonalLimitsEngine.KCAL_PER_G_FAT
        
        transfat_hard = eer * 0.01 / PersonalLimitsEngine.KCAL_PER_G_FAT
        
        flags = {
            "is_child": is_child,
            "risk_glucose": risk_glucose,
            "risk_cvd": risk_cvd,
            "risk_hypertension": risk_hypertension,
            "risk_pregnancy": risk_pregnancy,
            "bmi": round(bmi, 2),
            "age_years": age_years
        }
        
        return PersonalLimits(
            eer_kcal=round(eer, 2),
            sugar_soft_g=round(sugar_soft, 2),
            sugar_hard_g=round(sugar_hard, 2),
            sodium_soft_mg=round(sodium_soft, 2),
            sodium_hard_mg=round(sodium_hard, 2),
            satfat_soft_g=round(sat_soft, 2),
            satfat_hard_g=round(sat_hard, 2),
            transfat_hard_g=round(transfat_hard, 2),
            flags=flags
        )
