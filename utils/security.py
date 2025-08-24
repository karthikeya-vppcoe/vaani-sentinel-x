"""
Security utilities and configuration for Vaani Sentinel X.
Production-ready security measures.
"""

import os
import secrets
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import jwt


class SecurityManager:
    """Centralized security management."""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """Initialize security manager with encryption capabilities."""
        self.encryption_key = encryption_key
        if encryption_key:
            self.fernet = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        else:
            # Generate a new key if none provided
            self.fernet = Fernet(Fernet.generate_key())
    
    @staticmethod
    def generate_secure_key() -> str:
        """Generate a cryptographically secure key."""
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    
    @staticmethod
    def generate_password_hash(password: str, salt: Optional[bytes] = None) -> tuple[str, str]:
        """Generate a secure password hash with salt."""
        if salt is None:
            salt = secrets.token_bytes(32)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key.decode(), base64.urlsafe_b64encode(salt).decode()
    
    @staticmethod
    def verify_password(password: str, hashed_password: str, salt: str) -> bool:
        """Verify a password against its hash."""
        try:
            salt_bytes = base64.urlsafe_b64decode(salt.encode())
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt_bytes,
                iterations=100000,
            )
            expected_key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            return expected_key.decode() == hashed_password
        except Exception:
            return False
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt string data."""
        return self.fernet.encrypt(data.encode()).decode()
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt string data."""
        return self.fernet.decrypt(encrypted_data.encode()).decode()
    
    @staticmethod
    def create_jwt_token(payload: Dict[str, Any], secret: str, expires_in: int = 3600) -> str:
        """Create a JWT token with expiration."""
        payload = payload.copy()
        payload['exp'] = datetime.utcnow() + timedelta(seconds=expires_in)
        payload['iat'] = datetime.utcnow()
        return jwt.encode(payload, secret, algorithm='HS256')
    
    @staticmethod
    def verify_jwt_token(token: str, secret: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token."""
        try:
            return jwt.decode(token, secret, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for security."""
        # Remove path traversal attempts
        filename = os.path.basename(filename)
        
        # Remove dangerous characters
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\0']
        for char in dangerous_chars:
            filename = filename.replace(char, '_')
        
        # Limit length
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:250] + ext
        
        return filename
    
    @staticmethod
    def validate_content_security(content: str) -> Dict[str, Any]:
        """Validate content for security issues."""
        security_issues = []
        
        # Check for potential script injection
        dangerous_patterns = [
            '<script', '</script>',
            'javascript:', 'vbscript:',
            'onload=', 'onerror=', 'onclick=',
            'eval(', 'exec(', 'import(',
            '<?php', '<?=',
            '<iframe', '</iframe>',
        ]
        
        content_lower = content.lower()
        for pattern in dangerous_patterns:
            if pattern in content_lower:
                security_issues.append(f"Potential script injection: {pattern}")
        
        # Check for potential SQL injection
        sql_patterns = [
            "'; drop table", "' or '1'='1",
            "union select", "select * from",
            "delete from", "update set",
            "insert into", "create table",
        ]
        
        for pattern in sql_patterns:
            if pattern in content_lower:
                security_issues.append(f"Potential SQL injection: {pattern}")
        
        # Check content length
        if len(content) > 10000:  # 10KB limit
            security_issues.append("Content exceeds maximum length")
        
        return {
            'safe': len(security_issues) == 0,
            'issues': security_issues,
            'content_hash': hashlib.sha256(content.encode()).hexdigest()[:16]
        }


class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self):
        self.requests = {}
    
    def is_allowed(self, identifier: str, max_requests: int = 100, window_seconds: int = 3600) -> bool:
        """Check if request is allowed under rate limit."""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=window_seconds)
        
        # Clean old entries
        if identifier in self.requests:
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier]
                if req_time > window_start
            ]
        else:
            self.requests[identifier] = []
        
        # Check current count
        current_requests = len(self.requests[identifier])
        
        if current_requests >= max_requests:
            return False
        
        # Add current request
        self.requests[identifier].append(now)
        return True


class SecurityAudit:
    """Security audit utilities."""
    
    @staticmethod
    def audit_file_permissions(file_path: str) -> Dict[str, Any]:
        """Audit file permissions for security."""
        try:
            stat_info = os.stat(file_path)
            mode = stat_info.st_mode
            
            # Check if file is world-readable
            world_readable = bool(mode & 0o004)
            world_writable = bool(mode & 0o002)
            world_executable = bool(mode & 0o001)
            
            return {
                'path': file_path,
                'mode': oct(mode)[-3:],
                'world_readable': world_readable,
                'world_writable': world_writable,
                'world_executable': world_executable,
                'secure': not (world_writable or (world_readable and file_path.endswith(('.key', '.env', '.secret'))))
            }
        except OSError as e:
            return {
                'path': file_path,
                'error': str(e),
                'secure': False
            }
    
    @staticmethod
    def scan_sensitive_files(directory: str) -> List[Dict[str, Any]]:
        """Scan directory for sensitive files with insecure permissions."""
        sensitive_patterns = ['.env', '.key', '.pem', '.crt', 'secret', 'password', 'token']
        issues = []
        
        for root, dirs, files in os.walk(directory):
            # Skip hidden directories and venv
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'venv']
            
            for file in files:
                file_path = os.path.join(root, file)
                
                # Check if file matches sensitive patterns
                if any(pattern in file.lower() for pattern in sensitive_patterns):
                    audit_result = SecurityAudit.audit_file_permissions(file_path)
                    if not audit_result.get('secure', False):
                        issues.append(audit_result)
        
        return issues