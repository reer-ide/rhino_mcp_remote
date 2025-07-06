"""
Configuration settings for the Remote Rhino MCP Server.
"""

import os
from typing import Optional

from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Server configuration
    host: str = Field(default="127.0.0.1", description="Server host")
    port: int = Field(default=8080, description="Server port")
    log_level: str = Field(default="info", description="Logging level")
    
    # Redis configuration
    redis_url: Optional[str] = Field(default=None, description="Redis connection URL")
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database number")
    
    # PostgreSQL configuration
    database_url: Optional[str] = Field(default=None, description="Database connection URL")
    db_host: str = Field(default="localhost", description="Database host")
    db_port: int = Field(default=5432, description="Database port")
    db_name: str = Field(default="rhinomcp", description="Database name")
    db_user: str = Field(default="rhinomcp", description="Database user")
    db_password: str = Field(default="", description="Database password")
    
    # Authentication
    jwt_secret: Optional[str] = Field(default=None, description="JWT secret key")
    
    # Google Cloud configuration
    google_cloud_project: Optional[str] = Field(default=None, description="Google Cloud Project ID")
    
    # Development settings
    debug: bool = Field(default=False, description="Enable debug mode")
    reload: bool = Field(default=False, description="Enable auto-reload in development")
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    @property
    def redis_connection_url(self) -> str:
        """Get Redis connection URL."""
        if self.redis_url:
            return self.redis_url
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    @property
    def database_connection_url(self) -> str:
        """Get database connection URL."""
        if self.database_url:
            return self.database_url
        
        password_part = f":{self.db_password}" if self.db_password else ""
        return f"postgresql+asyncpg://{self.db_user}{password_part}@{self.db_host}:{self.db_port}/{self.db_name}"


# Global settings instance
settings = Settings() 