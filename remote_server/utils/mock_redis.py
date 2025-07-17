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
        self.set_data: Dict[str, set] = {}
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
        """Mock get method with automatic cleanup."""
        if key in self.expiry and datetime.now() > self.expiry[key]:
            self.data.pop(key, None)
            self.hash_data.pop(key, None)
            self.set_data.pop(key, None)
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
    
    async def hset(self, name: str, key: Optional[str] = None, value: Optional[Any] = None, mapping: Optional[Dict[str, Any]] = None) -> int:
        """Mock hset method that supports both key/value and mapping, like redis-py."""
        if name not in self.hash_data:
            self.hash_data[name] = {}
        
        added_count = 0
        if mapping:
            if key is not None or value is not None:
                raise TypeError("hset() cannot be used with both a mapping and a key/value pair")
            for k, v in mapping.items():
                str_v = str(v)
                if k not in self.hash_data[name] or self.hash_data[name][k] != str_v:
                    added_count += 1
                self.hash_data[name][str(k)] = str_v
            return added_count

        if key is not None and value is not None:
            str_value = str(value)
            is_new_field = key not in self.hash_data[name]
            if is_new_field:
                added_count = 1
            self.hash_data[name][str(key)] = str_value
            return added_count
        
        if key is not None:
             raise ValueError("hset() with an odd number of args is not allowed")

        raise ValueError("hset() requires a mapping or key-value pairs.")
    
    async def hget(self, key: str, field: str) -> Optional[str]:
        """Mock hget method."""
        return self.hash_data.get(key, {}).get(field)
    
    async def hgetall(self, key: str) -> Dict[str, str]:
        """Mock hgetall method with automatic cleanup."""
        if key in self.expiry and datetime.now() > self.expiry[key]:
            self.data.pop(key, None)
            self.hash_data.pop(key, None)
            self.set_data.pop(key, None)
            self.expiry.pop(key, None)
            return {}
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
    
    async def sadd(self, key: str, *values: str) -> int:
        """Mock sadd method."""
        if key not in self.set_data:
            self.set_data[key] = set()
        added = 0
        for value in values:
            if value not in self.set_data[key]:
                self.set_data[key].add(value)
                added += 1
        return added
    
    async def smembers(self, key: str) -> set:
        """Mock smembers method."""
        return self.set_data.get(key, set())
    
    async def srem(self, key: str, *values: str) -> int:
        """Mock srem method."""
        if key not in self.set_data:
            return 0
        removed = 0
        for value in values:
            if value in self.set_data[key]:
                self.set_data[key].remove(value)
                removed += 1
        return removed
    
    async def keys(self, pattern: str = "*") -> list:
        """Mock keys method with basic pattern support."""
        import fnmatch
        all_keys = list(self.data.keys()) + list(self.hash_data.keys()) + list(self.set_data.keys())
        
        if pattern == "*":
            return all_keys
        
        # Simple pattern matching
        return [key for key in all_keys if fnmatch.fnmatch(key, pattern)]
    
    async def close(self):
        """Mock close method."""
        pass
    
    def clear_all_data(self):
        """Clear all stored data (for testing/development)."""
        self.data.clear()
        self.hash_data.clear()
        self.set_data.clear()
        self.expiry.clear()
    
    def get_data_summary(self) -> Dict[str, Any]:
        """Get a summary of stored data (for debugging)."""
        return {
            "total_keys": len(self.data),
            "total_hashes": len(self.hash_data),
            "total_sets": len(self.set_data),
            "total_expiries": len(self.expiry),
            "sample_keys": list(self.data.keys())[:5],
            "sample_hashes": list(self.hash_data.keys())[:5],
            "sample_sets": list(self.set_data.keys())[:5]
        }


# Global shared mock Redis instance for development
_shared_mock_redis = None

def create_mock_redis(*args, **kwargs) -> MockRedis:
    """Factory function to create a mock Redis client."""
    return MockRedis(*args, **kwargs)

def get_shared_mock_redis() -> MockRedis:
    """Get shared mock Redis instance for development."""
    global _shared_mock_redis
    if _shared_mock_redis is None:
        _shared_mock_redis = MockRedis()
    return _shared_mock_redis

def reset_shared_mock_redis():
    """Reset the shared mock Redis instance."""
    global _shared_mock_redis
    if _shared_mock_redis is not None:
        _shared_mock_redis.clear_all_data()
    _shared_mock_redis = None 