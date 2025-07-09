"""
Mock Redis client for local development when Redis is not available.
"""

import asyncio
from typing import Dict, Any, Optional
import json
from datetime import datetime, timedelta


class MockRedis:
    """Mock Redis client that stores data in memory for testing."""
    
    def __init__(self, *args, **kwargs):
        self.data: Dict[str, str] = {}
        self.hash_data: Dict[str, Dict[str, str]] = {}
        self.expiry: Dict[str, datetime] = {}
    
    async def ping(self) -> bool:
        """Mock ping method."""
        return True
    
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Mock set method."""
        self.data[key] = value
        if ex:
            self.expiry[key] = datetime.now() + timedelta(seconds=ex)
        return True
    
    async def get(self, key: str) -> Optional[str]:
        """Mock get method."""
        if key in self.expiry and datetime.now() > self.expiry[key]:
            self.data.pop(key, None)
            self.expiry.pop(key, None)
            return None
        return self.data.get(key)
    
    async def delete(self, key: str) -> int:
        """Mock delete method."""
        if key in self.data:
            self.data.pop(key)
            self.expiry.pop(key, None)
            return 1
        return 0
    
    async def hset(self, key: str, mapping: Dict[str, str]) -> int:
        """Mock hset method."""
        if key not in self.hash_data:
            self.hash_data[key] = {}
        self.hash_data[key].update(mapping)
        return len(mapping)
    
    async def hget(self, key: str, field: str) -> Optional[str]:
        """Mock hget method."""
        return self.hash_data.get(key, {}).get(field)
    
    async def hgetall(self, key: str) -> Dict[str, str]:
        """Mock hgetall method."""
        return self.hash_data.get(key, {})
    
    async def exists(self, key: str) -> int:
        """Mock exists method."""
        if key in self.data or key in self.hash_data:
            return 1
        return 0
    
    async def expire(self, key: str, seconds: int) -> int:
        """Mock expire method."""
        if key in self.data or key in self.hash_data:
            self.expiry[key] = datetime.now() + timedelta(seconds=seconds)
            return 1
        return 0
    
    async def close(self):
        """Mock close method."""
        pass


def create_mock_redis(*args, **kwargs) -> MockRedis:
    """Factory function to create a mock Redis client."""
    return MockRedis(*args, **kwargs) 