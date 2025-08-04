"""
License Management System for Remote Rhino MCP Server
Simple but functional license system for MVP/beta testing.
"""

import hashlib
import secrets
import json
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import logging
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class LicenseRegistration:
    """License registration model for hardware-bound authentication"""
    license_id: str
    user_id: str
    machine_fingerprint: str
    registered_at: datetime
    last_seen: datetime
    status: str = "active"  # active, revoked
    max_concurrent_files: int = 3
    tier: str = "beta"
    license_key: Optional[str] = None  # Store the actual license key for reference


@dataclass
class LicenseKey:
    """License key structure"""
    license_id: str
    key: str
    issued_to: str
    issued_at: datetime
    expires_at: Optional[datetime]
    max_concurrent_files: int = 10
    tier: str = "beta"  # beta, standard, pro
    features: Dict[str, bool] = None
    
    def __post_init__(self):
        if self.features is None:
            self.features = {
                "persistent_sessions": True,
                "auto_reconnection": True,
                "file_integrity_check": True,
                "api_access": True
            }


class LicenseKeyEncoder:
    """Encodes and decodes license key strings"""
    
    def __init__(self):
        self.algorithm = "HS256"
        self.secret_key = self._get_or_create_secret()
        
    def _get_or_create_secret(self) -> str:
        """Get or create a secret key for license signing"""
        # For MVP, use a simple approach. In production, this should be secured.
        secret_file = "license_secret.key"
        try:
            with open(secret_file, 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            # Generate new secret
            secret = secrets.token_hex(32)
            with open(secret_file, 'w') as f:
                f.write(secret)
            logger.info("Generated new license secret key")
            return secret
    
    def generate_license_key(self, 
                           issued_to: str, 
                           tier: str = "beta",
                           max_concurrent_files: int = 3,
                           validity_days: Optional[int] = None) -> LicenseKey:
        """Generate a new license key"""
        
        license_id = str(uuid.uuid4())
        issued_at = datetime.now()
        expires_at = None
        if validity_days:
            expires_at = issued_at + timedelta(days=validity_days)
        
        # Create license data
        license_data = {
            "license_id": license_id,
            "issued_to": issued_to,
            "issued_at": issued_at.isoformat(),
            "expires_at": expires_at.isoformat() if expires_at else None,
            "tier": tier,
            "max_concurrent_files": max_concurrent_files
        }
        
        # Generate license key (simple format for MVP)
        license_key = self._encode_license_key(license_data)
        
        return LicenseKey(
            license_id=license_id,
            key=license_key,
            issued_to=issued_to,
            issued_at=issued_at,
            expires_at=expires_at,
            max_concurrent_files=max_concurrent_files,
            tier=tier
        )
    
    def _encode_license_key(self, license_data: Dict[str, Any]) -> str:
        """Encode license data into a license key string"""
        import base64
        
        # Convert to JSON and encode
        json_data = json.dumps(license_data, sort_keys=True)
        encoded_data = base64.b64encode(json_data.encode()).decode()
        
        # Create signature
        signature = hashlib.sha256(
            (encoded_data + self.secret_key).encode()
        ).hexdigest()[:16]
        
        # Simpler format: RHINO-<base64_data>-<signature>
        # Use the full base64 string to avoid truncation
        return f"RHINO-{encoded_data}-{signature}"
    
    def validate_license_key(self, license_key: str) -> Optional[Dict[str, Any]]:
        """Validate and decode a license key"""
        try:
            # Check format
            if not license_key.startswith("RHINO-"):
                return None
            
            # Split into parts: RHINO-<base64_data>-<signature>
            parts = license_key.split("-")
            if len(parts) != 3:
                logger.warning(f"Invalid license key format: expected 3 parts, got {len(parts)}")
                return None
            
            encoded_data = parts[1]
            provided_signature = parts[2]
            
            # Verify signature
            expected_signature = hashlib.sha256(
                (encoded_data + self.secret_key).encode()
            ).hexdigest()[:16]
            
            if provided_signature != expected_signature:
                logger.warning(f"Invalid license key signature")
                return None
            
            # Decode data
            try:
                import base64
                decoded_json = base64.b64decode(encoded_data.encode()).decode()
                license_data = json.loads(decoded_json)
                
                # Check expiration
                if license_data.get("expires_at"):
                    expires_at = datetime.fromisoformat(license_data["expires_at"])
                    if datetime.now() > expires_at:
                        logger.warning(f"License key expired")
                        return None
                
                return license_data
                
            except Exception as e:
                logger.warning(f"Failed to decode license data: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Error validating license key: {e}")
            return None
    
    def validate_machine_fingerprint(self, provided_fingerprint: str) -> bool:
        """Validate a machine fingerprint format (basic validation)"""
        if not provided_fingerprint:
            return False
            
        # Check if it's a valid hex string (SHA-256 should be 64 characters)
        if len(provided_fingerprint) != 64:
            return False
            
        try:
            # Verify it's a valid hex string
            int(provided_fingerprint, 16)
            return True
        except ValueError:
            return False


class LicenseManager:
    """Manages the full lifecycle of licenses including registration, validation, and storage"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379", session_max_ttl: int = 86400 * 30):
        self.redis_url = redis_url
        self.redis_client = None
        self.use_mock_redis = False
        self.session_max_ttl = session_max_ttl
        self.license_key_validator = LicenseKeyValidator()
        self.license_key_encoder = LicenseKeyEncoder()

    async def _init_redis(self):
        """Initialize Redis client with fallback to mock Redis"""
        if self.redis_client is not None:
            return
        
        logger.info(f"LicenseManager: Attempting to connect to Redis: {self.redis_url}")
        
        try:
            import redis.asyncio as redis
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            # Test the connection with a short timeout
            await asyncio.wait_for(self.redis_client.ping(), timeout=5.0)
            logger.info(f"LicenseManager: Connected to Redis successfully: {self.redis_url}")
            self.use_mock_redis = False
        except Exception as e:
            logger.warning(f"LicenseManager: Failed to connect to Redis ({self.redis_url}): {e}")
            logger.info("LicenseManager: Falling back to mock Redis for development")
            
            # Ensure we clean up the failed connection
            if self.redis_client:
                try:
                    await self.redis_client.close()
                except:
                    pass
            
            # Initialize mock Redis
            from remote_server.utils.mock_redis import create_mock_redis
            self.redis_client = create_mock_redis()
            self.use_mock_redis = True
            logger.info("LicenseManager: Mock Redis initialized successfully")

    def generate_license_key(self, issued_to: str, tier: str, max_concurrent_files: int, validity_days: Optional[int]) -> LicenseKey:
        """Generates a new license key string"""
        return self.license_key_encoder.generate_license_key(
            issued_to, tier, max_concurrent_files, validity_days
        )

    async def register_license(self, license_key: str, user_id: str, machine_fingerprint: str) -> LicenseRegistration:
        """Register a license using a license key and validate it"""
        await self._init_redis()
        
        is_valid, license_data = self.license_key_validator.validate_license(license_key, machine_fingerprint)
        if not is_valid or not license_data:
            raise ValueError("Invalid license key or machine fingerprint mismatch")
        
        license_id = license_data["license_id"]
        
        existing = await self.redis_client.hgetall(f"license:{license_id}")
        if existing:
            stored_fingerprint = existing.get("machine_fingerprint")
            if stored_fingerprint != machine_fingerprint:
                raise ValueError("License already registered to a different machine")
            
            await self.redis_client.hset(f"license:{license_id}", "last_seen", datetime.now().isoformat())
            license_registration = LicenseRegistration(
                license_id=license_id,
                user_id=existing["user_id"],
                machine_fingerprint=existing["machine_fingerprint"],
                registered_at=datetime.fromisoformat(existing["registered_at"]),
                last_seen=datetime.now(),
                status=existing.get("status", "active"),
                max_concurrent_files=int(existing.get("max_concurrent_files", 3)),
                tier=existing.get("tier", "beta"),
                license_key=license_key
            )
        else:
            license_registration = LicenseRegistration(
                license_id=license_id,
                user_id=user_id,
                machine_fingerprint=machine_fingerprint,
                registered_at=datetime.now(),
                last_seen=datetime.now(),
                max_concurrent_files=license_data.get("max_concurrent_files", 3),
                tier=license_data.get("tier", "beta"),
                license_key=license_key
            )
            
            license_dict = asdict(license_registration)
            license_dict["registered_at"] = license_registration.registered_at.isoformat()
            license_dict["last_seen"] = license_registration.last_seen.isoformat()
            
            await self.redis_client.hset(f"license:{license_id}", mapping=license_dict)
            await self.redis_client.expire(f"license:{license_id}", self.session_max_ttl)
            
            logger.info(f"License registered: {license_id} for user {user_id} (tier: {license_registration.tier})")
        
        return license_registration

    async def validate_license(self, license_id: str, machine_fingerprint: str) -> bool:
        """Validate a license by ID and machine fingerprint"""
        await self._init_redis()
        
        license_data = await self.redis_client.hgetall(f"license:{license_id}")
        if not license_data:
            return False
        
        if license_data.get("status") != "active":
            return False
        
        stored_fingerprint = license_data.get("machine_fingerprint")
        if stored_fingerprint != machine_fingerprint:
            return False
        
        stored_license_key = license_data.get("license_key")
        if stored_license_key:
            is_valid, _ = self.license_key_validator.validate_license(stored_license_key, machine_fingerprint)
            return is_valid
        
        return True

    async def validate_license_key(self, license_key: str, machine_fingerprint: Optional[str] = None) -> tuple[bool, Optional[str]]:
        """Validate a license key directly and return license_id"""
        is_valid, license_data = self.license_key_validator.validate_license(license_key, machine_fingerprint)
        if is_valid and license_data:
            return True, license_data["license_id"]
        return False, None

    async def get_license(self, license_id: str) -> Optional[LicenseRegistration]:
        """Get license information by ID"""
        await self._init_redis()
        
        license_data = await self.redis_client.hgetall(f"license:{license_id}")
        if not license_data:
            return None
        
        return LicenseRegistration(
            license_id=license_id,
            user_id=license_data["user_id"],
            machine_fingerprint=license_data["machine_fingerprint"],
            registered_at=datetime.fromisoformat(license_data["registered_at"]),
            last_seen=datetime.fromisoformat(license_data["last_seen"]),
            status=license_data.get("status", "active"),
            max_concurrent_files=int(license_data.get("max_concurrent_files", 3)),
            tier=license_data.get("tier", "beta"),
            license_key=license_data.get("license_key")
        )

    async def deactivate_license(self, license_id: str, reason: str = "user_request"):
        """Deactivate a license by ID"""
        await self._init_redis()
        
        # Check if license exists
        license_data = await self.redis_client.hgetall(f"license:{license_id}")
        if not license_data:
            raise ValueError(f"License not found: {license_id}")
        
        # Check if already deactivated
        if license_data.get("status") == "deactivated":
            logger.warning(f"License already deactivated: {license_id}")
            return
        
        # Deactivate with timestamp and reason
        await self.redis_client.hset(f"license:{license_id}", mapping={
            "status": "deactivated",
            "deactivated_at": datetime.now().isoformat(),
            "deactivation_reason": reason
        })
        await self.redis_client.expire(f"license:{license_id}", self.session_max_ttl)
        logger.info(f"License deactivated: {license_id} (reason: {reason})")

class LicenseKeyValidator:
    """License validation for runtime use"""
    
    def __init__(self):
        self.license_manager = LicenseKeyEncoder()
    
    def validate_license(self, license_key: str, machine_fingerprint: Optional[str] = None) -> tuple[bool, Optional[Dict[str, Any]]]:
        """Validate license key and optional machine fingerprint"""
        
        # Validate license key format and signature
        license_data = self.license_manager.validate_license_key(license_key)
        if not license_data:
            return False, None
        
        # If machine fingerprint provided, validate its format
        if machine_fingerprint:
            if not self.license_manager.validate_machine_fingerprint(machine_fingerprint):
                logger.warning("Invalid machine fingerprint format")
                return False, None
        
        return True, license_data
    
    def extract_license_id(self, license_key: str) -> Optional[str]:
        """Extract license ID from license key"""
        license_data = self.license_manager.validate_license_key(license_key)
        if license_data:
            return license_data.get("license_id")
        return None


# CLI functionality for license management
def generate_beta_license(issued_to: str, validity_days: int = 90) -> LicenseKey:
    """Generate a beta license for testing"""
    manager = LicenseKeyEncoder()
    return manager.generate_license_key(
        issued_to=issued_to,
        tier="beta",
        max_concurrent_files=3,
        validity_days=validity_days
    )


def validate_license_cli(license_key: str) -> Dict[str, Any]:
    """CLI function to validate a license key"""
    validator = LicenseKeyValidator()
    is_valid, license_data = validator.validate_license(license_key)
    
    result = {
        "valid": is_valid,
        "license_data": license_data
    }
    
    return result


if __name__ == "__main__":
    # CLI interface for license management
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python license_manager.py generate <name> [days]")
        print("  python license_manager.py validate <license_key>")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "generate":
        if len(sys.argv) < 3:
            print("Usage: python license_manager.py generate <name> [days]")
            sys.exit(1)
        
        name = sys.argv[2]
        days = int(sys.argv[3]) if len(sys.argv) > 3 else 90
        
        license_key = generate_beta_license(name, days)
        
        print(f"Generated Beta License:")
        print(f"  License ID: {license_key.license_id}")
        print(f"  License Key: {license_key.key}")
        print(f"  Issued To: {license_key.issued_to}")
        print(f"  Tier: {license_key.tier}")
        print(f"  Max Concurrent Files: {license_key.max_concurrent_files}")
        print(f"  Issued At: {license_key.issued_at}")
        print(f"  Expires At: {license_key.expires_at}")
    
    elif command == "validate":
        if len(sys.argv) < 3:
            print("Usage: python license_manager.py validate <license_key>")
            sys.exit(1)
        
        license_key = sys.argv[2]
        result = validate_license_cli(license_key)
        
        print(f"License Validation Result:")
        print(f"  Valid: {result['valid']}")
        
        if result['license_data']:
            data = result['license_data']
            print(f"  License ID: {data.get('license_id')}")
            print(f"  Issued To: {data.get('issued_to')}")
            print(f"  Tier: {data.get('tier')}")
            print(f"  Max Concurrent Files: {data.get('max_concurrent_files')}")
            print(f"  Issued At: {data.get('issued_at')}")
            print(f"  Expires At: {data.get('expires_at', 'Never')}")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1) 