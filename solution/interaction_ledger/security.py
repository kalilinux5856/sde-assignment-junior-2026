import hashlib
import os
from pathlib import Path
from dotenv import load_dotenv
from cryptography.fernet import Fernet
PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")

def get_encryption_key():
    key = os.environ.get("PII_ENCRYPTION_KEY")

    if not key:
        raise RuntimeError(
            "PII_ENCRYPTION_KEY environment variable is missing"
        )

    return key.encode()


def hash_phone(phone: str) -> str:
    return hashlib.sha256(phone.encode("utf-8")).hexdigest()


def encrypt_pii(data: str) -> bytes:
    key = get_encryption_key()
    cipher = Fernet(key)

    return cipher.encrypt(data.encode("utf-8"))


def decrypt_pii(encrypted_data: bytes) -> str:
    key = get_encryption_key()
    cipher = Fernet(key)

    return cipher.decrypt(encrypted_data).decode("utf-8")