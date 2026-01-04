"""
Database field encryption utilities using AES-256-GCM with PBKDF2 key derivation.
Implements secure encryption for sensitive data fields.
"""

import base64
import os
from typing import Optional, Union
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes
from sqlalchemy.types import Text, TypeDecorator


class EncryptionManager:
    """Manages encryption/decryption operations for database fields."""
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize encryption manager with master key.
        
        Args:
            master_key: Master encryption key (from environment variable)
                       If None, will use EAGLEARN_ENCRYPTION_KEY env var
        """
        self.master_key = master_key or os.getenv('EAGLEARN_ENCRYPTION_KEY')
        if not self.master_key:
            raise ValueError(
                "Encryption key not found. Set EAGLEARN_ENCRYPTION_KEY environment variable."
            )
        
        # Derive encryption key using PBKDF2
        self.salt = b'eaglearn_salt_v1'  # In production, use unique salt per installation
        self.key = PBKDF2(
            self.master_key,
            self.salt,
            dkLen=32,  # 256 bits for AES-256
            count=100000  # PBKDF2 iterations
        )
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext using AES-256-GCM.
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Base64-encoded encrypted data with format: nonce||tag||ciphertext
        """
        if not plaintext:
            return plaintext
        
        # Generate random nonce (12 bytes for GCM)
        nonce = get_random_bytes(12)
        
        # Create cipher
        cipher = AES.new(self.key, AES.MODE_GCM, nonce=nonce)
        
        # Encrypt and get authentication tag
        ciphertext, tag = cipher.encrypt_and_digest(plaintext.encode('utf-8'))
        
        # Combine nonce + tag + ciphertext and encode as base64
        encrypted_data = nonce + tag + ciphertext
        return base64.b64encode(encrypted_data).decode('utf-8')
    
    def decrypt(self, encrypted: Union[str, bytes, memoryview]) -> str:
        """
        Decrypt ciphertext using AES-256-GCM.
        
        Args:
            encrypted: Base64-encoded encrypted data
            
        Returns:
            Decrypted plaintext string
            
        Raises:
            ValueError: If decryption fails (wrong key or tampered data)
        """
        if not encrypted:
            return encrypted

        try:
            # Decode from base64
            if isinstance(encrypted, memoryview):
                encrypted = encrypted.tobytes()
            if isinstance(encrypted, bytes):
                encrypted_bytes = encrypted
            else:
                encrypted_bytes = encrypted.encode('utf-8')
            encrypted_data = base64.b64decode(encrypted_bytes)
            
            # Extract nonce (12 bytes), tag (16 bytes), and ciphertext
            nonce = encrypted_data[:12]
            tag = encrypted_data[12:28]
            ciphertext = encrypted_data[28:]
            
            # Create cipher and decrypt
            cipher = AES.new(self.key, AES.MODE_GCM, nonce=nonce)
            plaintext = cipher.decrypt_and_verify(ciphertext, tag)
            
            return plaintext.decode('utf-8')
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")


# Global encryption manager instance
_encryption_manager: Optional[EncryptionManager] = None


def get_encryption_manager() -> EncryptionManager:
    """Get or create global encryption manager instance."""
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()
    return _encryption_manager


class EncryptedString(TypeDecorator):
    """
    SQLAlchemy custom type for encrypted string fields.
    Automatically encrypts on write and decrypts on read.
    """
    
    impl = Text
    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        """Encrypt value before storing in database."""
        if value is not None:
            manager = get_encryption_manager()
            return manager.encrypt(value)
        return value
    
    def process_result_value(self, value, dialect):
        """Decrypt value after reading from database."""
        if value is not None:
            manager = get_encryption_manager()
            return manager.decrypt(value)
        return value
