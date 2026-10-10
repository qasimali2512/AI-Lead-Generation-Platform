from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


class CredentialEncryptionError(Exception):
    """Raised when credential encryption/decryption fails."""


def _get_fernet() -> Fernet:
    key = settings.email_credential_encryption_key.encode("utf-8")

    try:
        return Fernet(key)
    except Exception as exc:
        raise CredentialEncryptionError(
            "Invalid EMAIL_CREDENTIAL_ENCRYPTION_KEY."
        ) from exc


def encrypt_credential(value: str | None) -> str | None:
    if value is None:
        return None

    if not value:
        return ""

    try:
        return _get_fernet().encrypt(
            value.encode("utf-8")
        ).decode("utf-8")
    except Exception as exc:
        raise CredentialEncryptionError(
            "Unable to encrypt credential."
        ) from exc


def decrypt_credential(value: str | None) -> str | None:
    if value is None:
        return None

    if not value:
        return ""

    try:
        return _get_fernet().decrypt(
            value.encode("utf-8")
        ).decode("utf-8")
    except InvalidToken as exc:
        raise CredentialEncryptionError(
            "Unable to decrypt credential."
        ) from exc
    except Exception as exc:
        raise CredentialEncryptionError(
            "Unable to decrypt credential."
        ) from exc