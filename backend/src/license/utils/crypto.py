"""
License Cryptographic Utilities

Implements ECDSA signature verification for license keys using embedded public key.
Supports offline validation without network calls.
"""

import base64
import hashlib
from typing import Tuple, Optional
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature

from ..models.license_model import ParsedLicenseKey
from ..consts import LicenseErrorCode


class LicenseCryptoError(Exception):
    """Exception raised for cryptographic errors."""
    def __init__(self, message: str, error_code: str = LicenseErrorCode.SIGNATURE_INVALID):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class LicenseCrypto:
    """
    Cryptographic operations for license key validation.
    
    Uses ECDSA with P-256 curve for signature verification.
    The public key is embedded in the application for offline validation.
    """
    
    def __init__(self, public_key_pem: Optional[str] = None):
        """
        Initialize with public key for verification.
        
        Args:
            public_key_pem: PEM-encoded public key string. If None, uses embedded key.
        """
        from .keys import get_public_key_pem
        
        pem = public_key_pem or get_public_key_pem()
        self._public_key = self._load_public_key(pem)
    
    def _load_public_key(self, pem: str) -> ec.EllipticCurvePublicKey:
        """Load public key from PEM string."""
        try:
            key = serialization.load_pem_public_key(
                pem.encode('utf-8'),
                backend=default_backend()
            )
            if not isinstance(key, ec.EllipticCurvePublicKey):
                raise LicenseCryptoError("Invalid key type: expected ECDSA public key")
            return key
        except Exception as e:
            raise LicenseCryptoError(f"Failed to load public key: {e}")
    
    def verify_signature(self, parsed_key: ParsedLicenseKey) -> bool:
        """
        Verify the cryptographic signature of a parsed license key.
        
        Args:
            parsed_key: The parsed license key with signature
            
        Returns:
            True if signature is valid
            
        Raises:
            LicenseCryptoError: If signature verification fails
        """
        try:
            # Get the data that was signed
            data_to_verify = parsed_key.get_data_to_sign()
            
            # Decode the signature from base64
            signature = self._decode_signature(parsed_key.signature)
            
            # Verify the signature
            self._public_key.verify(
                signature,
                data_to_verify.encode('utf-8'),
                ec.ECDSA(hashes.SHA256())
            )
            
            return True
            
        except InvalidSignature:
            raise LicenseCryptoError(
                "License signature verification failed",
                LicenseErrorCode.SIGNATURE_INVALID
            )
        except Exception as e:
            raise LicenseCryptoError(f"Signature verification error: {e}")
    
    def _decode_signature(self, signature_b64: str) -> bytes:
        """Decode base64 signature, handling URL-safe and standard variants."""
        # Add padding if needed
        padding = 4 - (len(signature_b64) % 4)
        if padding != 4:
            signature_b64 += '=' * padding
        
        try:
            # Try URL-safe base64 first
            return base64.urlsafe_b64decode(signature_b64)
        except Exception:
            try:
                # Fall back to standard base64
                return base64.b64decode(signature_b64)
            except Exception as e:
                raise LicenseCryptoError(f"Invalid signature encoding: {e}")
    
    def is_signature_valid(self, parsed_key: ParsedLicenseKey) -> Tuple[bool, Optional[str]]:
        """
        Check if signature is valid without raising exceptions.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            self.verify_signature(parsed_key)
            return True, None
        except LicenseCryptoError as e:
            return False, e.message
        except Exception as e:
            return False, str(e)


def hash_license_key(license_key: str) -> str:
    """
    Create a SHA-256 hash of a license key for storage.
    
    Never store raw license keys - always hash them.
    """
    return hashlib.sha256(license_key.encode('utf-8')).hexdigest()


def verify_key_hash(license_key: str, stored_hash: str) -> bool:
    """
    Verify a license key against a stored hash.
    """
    return hash_license_key(license_key) == stored_hash
