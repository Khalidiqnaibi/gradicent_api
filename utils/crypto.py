"""
crypto.py
----------
Fernet helpers. Keep keys/config in config.py and don't hardcode secrets.
"""

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import base64

def build_fernet(secret: str, salt: bytes) -> Fernet:
    """
    Build a Fernet instance from a human-friendly secret.
    
    Expects:
    - secret: str - human-friendly secret phrase
    - salt: bytes - random bytes, stored in config.py
    
    outputs:
    - Fernet instance
    """
    password = secret.encode()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        iterations=100_000,
        salt=salt,
        length=32
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))
    return Fernet(key)

def encrypt(fernet: Fernet, payload: str) -> bytes:
    """
    Encrypt a payload using the provided Fernet instance.
    
    Expects:
    - payload: str - the string payload to encrypt
    outputs:
    - bytes - the encrypted token
    """
    return fernet.encrypt(payload.encode())

def decrypt(fernet: Fernet, token: bytes) -> str | None:
    """
    Decrypt a token using the provided Fernet instance.

    Expects:
    - token: bytes - the encrypted token to decrypt
    
    outputs:
    - str | None - the decrypted payload as a string.
    
    Returns None if decryption fails.
    """
    try:
        return fernet.decrypt(token).decode()
    except InvalidToken:
        return None
