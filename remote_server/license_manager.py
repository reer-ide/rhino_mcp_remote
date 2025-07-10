"""
License Management System for Remote Rhino MCP Server
Simple but functional license system for MVP/beta testing.
"""

import hashlib
import secrets
import platform
import subprocess
import json
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class LicenseKey:
    """License key structure"""
    license_id: str
    key: str
    issued_to: str
    issued_at: datetime
    expires_at: Optional[datetime]
    max_concurrent_files: int = 3
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


class LicenseManager:
    """Simple license management for MVP/beta testing"""
    
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
    
    def get_machine_fingerprint(self) -> str:
        """Generate machine fingerprint for hardware binding"""
        try:
            # Collect system information
            system_info = {
                "platform": platform.platform(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "node": platform.node()
            }
            
            # Try to get additional hardware info
            try:
                if platform.system() == "Windows":
                    # Get CPU ID and disk serial on Windows
                    result = subprocess.run(
                        ["wmic", "cpu", "get", "ProcessorId", "/value"],
                        capture_output=True, text=True, timeout=5
                    )
                    cpu_info = result.stdout.strip()
                    system_info["cpu_id"] = cpu_info
                    
                    result = subprocess.run(
                        ["wmic", "diskdrive", "get", "SerialNumber", "/value"],
                        capture_output=True, text=True, timeout=5
                    )
                    disk_info = result.stdout.strip()
                    system_info["disk_serial"] = disk_info
                    
                elif platform.system() == "Darwin":  # macOS
                    result = subprocess.run(
                        ["system_profiler", "SPHardwareDataType"],
                        capture_output=True, text=True, timeout=5
                    )
                    system_info["hardware_info"] = result.stdout[:200]
                    
                elif platform.system() == "Linux":
                    # Try to get machine-id
                    try:
                        with open("/etc/machine-id", "r") as f:
                            system_info["machine_id"] = f.read().strip()
                    except:
                        pass
                        
            except Exception as e:
                logger.warning(f"Failed to get detailed hardware info: {e}")
            
            # Create fingerprint hash
            fingerprint_data = json.dumps(system_info, sort_keys=True)
            fingerprint = hashlib.sha256(fingerprint_data.encode()).hexdigest()
            
            logger.info(f"Generated machine fingerprint: {fingerprint[:16]}...")
            return fingerprint
            
        except Exception as e:
            logger.error(f"Failed to generate machine fingerprint: {e}")
            # Fallback to basic info
            fallback_data = f"{platform.platform()}-{platform.machine()}-{platform.node()}"
            return hashlib.sha256(fallback_data.encode()).hexdigest()


class LicenseValidator:
    """License validation for runtime use"""
    
    def __init__(self):
        self.license_manager = LicenseManager()
        self._cached_fingerprint = None
    
    def get_machine_fingerprint(self) -> str:
        """Get cached machine fingerprint"""
        if self._cached_fingerprint is None:
            self._cached_fingerprint = self.license_manager.get_machine_fingerprint()
        return self._cached_fingerprint
    
    def validate_license(self, license_key: str, machine_fingerprint: Optional[str] = None) -> tuple[bool, Optional[Dict[str, Any]]]:
        """Validate license key and optional machine fingerprint"""
        
        # Validate license key format and signature
        license_data = self.license_manager.validate_license_key(license_key)
        if not license_data:
            return False, None
        
        # If machine fingerprint provided, validate it
        if machine_fingerprint:
            current_fingerprint = self.get_machine_fingerprint()
            if machine_fingerprint != current_fingerprint:
                logger.warning("Machine fingerprint mismatch")
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
    manager = LicenseManager()
    return manager.generate_license_key(
        issued_to=issued_to,
        tier="beta",
        max_concurrent_files=3,
        validity_days=validity_days
    )


def validate_license_cli(license_key: str) -> Dict[str, Any]:
    """CLI function to validate a license key"""
    validator = LicenseValidator()
    is_valid, license_data = validator.validate_license(license_key)
    
    result = {
        "valid": is_valid,
        "license_data": license_data,
        "machine_fingerprint": validator.get_machine_fingerprint()
    }
    
    return result


if __name__ == "__main__":
    # CLI interface for license management
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python license_manager.py generate <name> [days]")
        print("  python license_manager.py validate <license_key>")
        print("  python license_manager.py fingerprint")
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
        print(f"  Machine Fingerprint: {result['machine_fingerprint'][:16]}...")
        
        if result['license_data']:
            data = result['license_data']
            print(f"  License ID: {data.get('license_id')}")
            print(f"  Issued To: {data.get('issued_to')}")
            print(f"  Tier: {data.get('tier')}")
            print(f"  Max Concurrent Files: {data.get('max_concurrent_files')}")
            print(f"  Issued At: {data.get('issued_at')}")
            print(f"  Expires At: {data.get('expires_at', 'Never')}")
    
    elif command == "fingerprint":
        validator = LicenseValidator()
        fingerprint = validator.get_machine_fingerprint()
        print(f"Machine Fingerprint: {fingerprint}")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1) 