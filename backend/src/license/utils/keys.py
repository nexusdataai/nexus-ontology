"""
License Key Management

Contains embedded public key for offline license validation.
Supports key rotation via configuration.
"""

import os
from typing import Optional

# Default embedded keypair for license verification (ECDSA P-256)
# This keypair is used for development/testing when no external key is configured.
# In production, set LICENSE_PUBLIC_KEY and LICENSE_PRIVATE_KEY env vars.
_DEFAULT_PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAESOCtaAr0OLS7kQ0SDSO3N4kMdBDH
nf+nkPoLlXX40TajRIxPSDD5MCwCFBfm1WBvsQaeKMRsJqv2F92KB0ce/Q==
-----END PUBLIC KEY-----"""

_DEFAULT_PRIVATE_KEY_PEM = """-----BEGIN PRIVATE KEY-----
MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQg575nRDUIwDyJFsLo
3Uci93h9hYsYWMTbC9ChGJHW2mWhRANCAARI4K1oCvQ4tLuRDRINI7c3iQx0EMed
/6eQ+guVdfjRNqNEjE9IMPkwLAIUF+bVYG+xBp4oxGwmq/YX3YoHRx79
-----END PRIVATE KEY-----"""

# Environment variable for custom public key
PUBLIC_KEY_ENV_VAR = "LICENSE_PUBLIC_KEY"
PUBLIC_KEY_FILE_ENV_VAR = "LICENSE_PUBLIC_KEY_FILE"
PRIVATE_KEY_ENV_VAR = "LICENSE_PRIVATE_KEY"


def get_public_key_pem() -> str:
    """
    Get the public key PEM for license verification.
    
    Priority:
    1. LICENSE_PUBLIC_KEY environment variable (direct PEM content)
    2. LICENSE_PUBLIC_KEY_FILE environment variable (path to PEM file)
    3. Default embedded key
    
    Returns:
        PEM-encoded public key string
    """
    # Check for direct PEM in environment
    env_key = os.environ.get(PUBLIC_KEY_ENV_VAR)
    if env_key:
        return env_key
    
    # Check for key file path
    key_file = os.environ.get(PUBLIC_KEY_FILE_ENV_VAR)
    if key_file and os.path.exists(key_file):
        with open(key_file, 'r') as f:
            return f.read()
    
    # Return default embedded key
    return _DEFAULT_PUBLIC_KEY_PEM


def set_public_key(pem: str) -> None:
    """
    Set the public key via environment variable.
    
    Useful for testing or runtime key rotation.
    """
    os.environ[PUBLIC_KEY_ENV_VAR] = pem


def get_private_key_pem() -> str:
    """
    Get the private key PEM for license key generation (development/testing only).
    
    Priority:
    1. LICENSE_PRIVATE_KEY environment variable
    2. Default embedded key (for development)
    
    Returns:
        PEM-encoded private key string
    """
    env_key = os.environ.get(PRIVATE_KEY_ENV_VAR)
    if env_key:
        return env_key
    return _DEFAULT_PRIVATE_KEY_PEM


def clear_public_key() -> None:
    """
    Clear any custom public key, reverting to default.
    """
    if PUBLIC_KEY_ENV_VAR in os.environ:
        del os.environ[PUBLIC_KEY_ENV_VAR]
    if PUBLIC_KEY_FILE_ENV_VAR in os.environ:
        del os.environ[PUBLIC_KEY_FILE_ENV_VAR]


# For testing: Generate a new key pair
def generate_key_pair() -> tuple:
    """
    Generate a new ECDSA key pair for testing.
    
    Returns:
        Tuple of (private_key_pem, public_key_pem)
    """
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    
    # Generate private key
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    
    # Serialize private key
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    
    # Get public key
    public_key = private_key.public_key()
    
    # Serialize public key
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    return private_pem, public_pem
