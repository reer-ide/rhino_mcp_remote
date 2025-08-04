"""
License management endpoints for Remote Rhino MCP Server.
"""

from fastmcp import FastMCP
from fastmcp.utilities.logging import get_logger
from starlette.requests import Request
from starlette.responses import JSONResponse

from remote_server.dependencies import get_license_manager

logger = get_logger(__name__)


def register_license_routes(mcp: FastMCP):
    """Register license management routes with the FastMCP server."""
    
    @mcp.custom_route("/license/generate", methods=["POST"])
    async def generate_license_key(request: Request) -> JSONResponse:
        """Generate a new license key (for testing/admin purposes)"""
        try:
            license_manager = await get_license_manager()
                
            data = await request.json()
            issued_to = data.get("issued_to")
            tier = data.get("tier", "beta")
            validity_days = data.get("validity_days", 90)
            max_concurrent_files = data.get("max_concurrent_files", 3)
            
            if not issued_to:
                return JSONResponse(
                    {"error": "issued_to is required"},
                    status_code=400
                )
            
            # Generate license key
            license_key = license_manager.generate_license_key(
                issued_to=issued_to,
                tier=tier,
                max_concurrent_files=max_concurrent_files,
                validity_days=validity_days
            )
            
            return JSONResponse({
                "license_id": license_key.license_id,
                "license_key": license_key.key,
                "issued_to": license_key.issued_to,
                "tier": license_key.tier,
                "max_concurrent_files": license_key.max_concurrent_files,
                "issued_at": license_key.issued_at.isoformat(),
                "expires_at": license_key.expires_at.isoformat() if license_key.expires_at else None,
                "features": license_key.features
            })
            
        except Exception as e:
            logger.error(f"Error generating license key: {e}")
            return JSONResponse(
                {"error": f"Failed to generate license key: {str(e)}"}, 
                status_code=500
            )
        
    @mcp.custom_route("/license/register", methods=["POST"])
    async def register_license(request: Request) -> JSONResponse:
        """Register a license using a license key"""
        try:
            license_manager = await get_license_manager()
                
            data = await request.json()
            license_key = data.get("license_key")
            user_id = data.get("user_id")
            machine_fingerprint = data.get("machine_fingerprint")
            
            if not license_key or not user_id or not machine_fingerprint:
                return JSONResponse(
                    {"error": "license_key, user_id, and machine_fingerprint are required"},
                    status_code=400
                )
            
            license_registration = await license_manager.register_license(
                license_key, user_id, machine_fingerprint
            )
            
            # TODO: send a success message to notify the host app

            return JSONResponse({
                "status": "success",
                "license_id": license_registration.license_id,
                "user_id": license_registration.user_id,
                "tier": license_registration.tier,
                "registered_at": license_registration.registered_at.isoformat(),
                "max_concurrent_files": license_registration.max_concurrent_files
            })
            
        except ValueError as e:
            return JSONResponse(
                {"error": str(e)}, 
                status_code=400
            )
        except Exception as e:
            logger.error(f"Error registering license: {e}")
            return JSONResponse(
                {"error": f"Failed to register license: {str(e)}"}, 
                status_code=500
            )

    @mcp.custom_route("/license/validate", methods=["POST"])
    async def validate_license(request: Request) -> JSONResponse:
        """Validate a license key or license ID with machine fingerprint"""
        try:
            license_manager = await get_license_manager()
            data = await request.json()
            license_key = data.get("license_key")
            license_id = data.get("license_id")
            machine_fingerprint = data.get("machine_fingerprint")
            
            if not machine_fingerprint:
                return JSONResponse(
                    {"error": "machine_fingerprint is required"},
                    status_code=400
                )
            if not license_id:
                return JSONResponse(
                    {"error": "license_id is required"},
                    status_code=400
                )
            if not license_key:
                return JSONResponse(
                    {"error": "license_key is required"},
                    status_code=400
                )
            
            # check if license_id is registered in Redis
            license_data = await license_manager.get_license(license_id)
            if license_data:
                # Validate using license key
                is_valid, validation_license_id = await license_manager.validate_license_key(
                    license_key, machine_fingerprint
                )
                if is_valid:
                        return JSONResponse({
                            "status": "valid",
                            "license_id": validation_license_id,
                            "user_id": license_data.user_id,
                            "tier": license_data.tier,
                            "last_seen": license_data.last_seen.isoformat()
                        })
                else:
                    return JSONResponse({
                        "status": "invalid",
                        "message": "Invalid license key or machine fingerprint mismatch"
                    }, status_code=401)
            else:
                return JSONResponse({
                    "status": "invalid",
                    "message": "License not found"
                }, status_code=401)
        except Exception as e:
            logger.error(f"Error validating license: {e}")
            return JSONResponse(
                {"error": "Failed to validate license"}, 
                status_code=500
            )

    @mcp.custom_route("/license/{license_id}/info", methods=["GET"])
    async def get_license_info(request: Request) -> JSONResponse:
        """Get license information"""
        try:
            license_manager = await get_license_manager()
            license_id = request.path_params["license_id"]
            license_data = await license_manager.get_license(license_id)
            
            if not license_data:
                return JSONResponse(
                    {"error": "License not found"}, 
                    status_code=404
                )
            
            return JSONResponse({
                "license_id": license_data.license_id,
                "user_id": license_data.user_id,
                "status": license_data.status,
                "tier": license_data.tier,
                "registered_at": license_data.registered_at.isoformat(),
                "last_seen": license_data.last_seen.isoformat(),
                "max_concurrent_files": license_data.max_concurrent_files
            })
            
        except Exception as e:
            logger.error(f"Error getting license info: {e}")
            return JSONResponse(
                {"error": "Failed to get license info"}, 
                status_code=500
            )
        
    @mcp.custom_route("/license/{license_id}/deactivate", methods=["POST"])
    async def deactivate_license(request: Request) -> JSONResponse:
        """Deactivate a license"""
        try:
            license_manager = await get_license_manager()
            license_id = request.path_params["license_id"]
            
            # Extract optional reason from request body
            reason = "user_request"  # default
            try:
                data = await request.json()
                reason = data.get("reason", "user_request")
            except:
                # If no JSON body provided, use default reason
                pass
            
            await license_manager.deactivate_license(license_id, reason)

            # TODO: send a success message to notify the host app

            return JSONResponse({
                "status": "success",
                "license_id": license_id,
                "reason": reason
            })
        except ValueError as e:
            return JSONResponse(
                {"error": str(e)}, 
                status_code=404
            )
        except Exception as e:
            logger.error(f"Error deactivating license: {e}")
            return JSONResponse(
                {"error": "Failed to deactivate license"}, 
                status_code=500
            )