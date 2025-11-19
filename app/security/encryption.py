from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import hashlib
from app.config import settings


class EncryptionService:
    def __init__(self):
        # Gunakan encryption_key sebagai "master secret", bukan base64
        secret = settings.encryption_key.encode("utf-8")

        # Salt harus konstan dan stabil (jangan random tiap run)
        salt = b"nuca-v1-fixed-salt"

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=390000,
            backend=default_backend(),
        )

        # Derive key lalu jadikan key Fernet
        key = base64.urlsafe_b64encode(kdf.derive(secret))
        self.cipher = Fernet(key)

    def encrypt(self, data: str) -> str:
        if data is None:
            return None
        return self.cipher.encrypt(data.encode()).decode()

    def decrypt(self, encrypted_data: str) -> str:
        if encrypted_data is None:
            return None
        return self.cipher.decrypt(encrypted_data.encode()).decode()

    def encrypt_boolean(self, value: bool) -> str:
        if value is None:
            return None
        return self.encrypt(str(value))

    def decrypt_boolean(self, encrypted_value: str) -> bool:
        if encrypted_value is None:
            return None
        decrypted = self.decrypt(encrypted_value)
        return decrypted.lower() == "true"

    def encrypt_decimal(self, value: float) -> str:
        if value is None:
            return None
        return self.encrypt(str(value))

    def decrypt_decimal(self, encrypted_value: str) -> float:
        if encrypted_value is None:
            return None
        decrypted = self.decrypt(encrypted_value)
        return float(decrypted)

    def hash_pii(self, data: str) -> str:
        if data is None:
            return None
        return hashlib.sha256(data.encode()).hexdigest()


encryption_service = EncryptionService()


def encrypt_profile_health_data(profile_data: dict) -> dict:
    encrypted = profile_data.copy()

    if "date_of_birth" in profile_data and profile_data["date_of_birth"]:
        encrypted["date_of_birth_encrypted"] = encryption_service.encrypt(
            profile_data["date_of_birth"].isoformat()
        )
        del encrypted["date_of_birth"]

    if "height_cm" in profile_data and profile_data["height_cm"] is not None:
        encrypted["height_cm_encrypted"] = encryption_service.encrypt_decimal(
            profile_data["height_cm"]
        )
        del encrypted["height_cm"]

    if "weight_kg" in profile_data and profile_data["weight_kg"] is not None:
        encrypted["weight_kg_encrypted"] = encryption_service.encrypt_decimal(
            profile_data["weight_kg"]
        )
        del encrypted["weight_kg"]

    health_flags = [
        "has_hypertension",
        "has_diabetes",
        "has_heart_disease",
        "has_kidney_disease",
        "is_pregnant",
    ]

    for flag in health_flags:
        if flag in profile_data and profile_data[flag] is not None:
            encrypted[f"{flag}_encrypted"] = encryption_service.encrypt_boolean(
                profile_data[flag]
            )
            del encrypted[flag]

    return encrypted


def decrypt_profile_health_data(profile_db) -> dict:
    decrypted = {}

    if (
        hasattr(profile_db, "date_of_birth_encrypted")
        and profile_db.date_of_birth_encrypted
    ):
        from datetime import date

        dob_str = encryption_service.decrypt(profile_db.date_of_birth_encrypted)
        decrypted["date_of_birth"] = date.fromisoformat(dob_str)

    if hasattr(profile_db, "height_cm_encrypted") and profile_db.height_cm_encrypted:
        decrypted["height_cm"] = encryption_service.decrypt_decimal(
            profile_db.height_cm_encrypted
        )

    if hasattr(profile_db, "weight_kg_encrypted") and profile_db.weight_kg_encrypted:
        decrypted["weight_kg"] = encryption_service.decrypt_decimal(
            profile_db.weight_kg_encrypted
        )

    health_flags = [
        "has_hypertension",
        "has_diabetes",
        "has_heart_disease",
        "has_kidney_disease",
        "is_pregnant",
    ]

    for flag in health_flags:
        encrypted_attr = f"{flag}_encrypted"
        if hasattr(profile_db, encrypted_attr):
            encrypted_value = getattr(profile_db, encrypted_attr)
            if encrypted_value:
                decrypted[flag] = encryption_service.decrypt_boolean(encrypted_value)

    return decrypted
