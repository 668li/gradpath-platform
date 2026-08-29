# backend/app/core/secret_crypto.py
"""对称加密工具 — 用于用户自带的 LLM API Key 落库加密。

密钥从 ``settings.SECRET_KEY`` 派生（SHA-256 → Fernet key），无需额外密钥配置。
加密结果为 URL-safe base64 token，明文密钥不落库。
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plain: str) -> str:
    """加密明文密钥，返回 URL-safe base64 token。"""
    return _fernet().encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt_secret(token: str) -> str:
    """解密 token；SECRET_KEY 变更导致无法解密时返回空串（视为配置失效）。"""
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        return ""


def mask_secret(plain: str) -> str:
    """掩码展示：保留末 4 位，如 ``sk-****abcd``。"""
    if len(plain) <= 4:
        return "****"
    return f"****{plain[-4:]}"
