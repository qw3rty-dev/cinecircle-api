import json
from typing import Any

import redis.asyncio as redis


async def set_cache(key:str, ttl: int, value: Any, redis_client:redis):
    try:
        json_value = json.dumps(value)
        await redis_client.set(key, json_value, ex=ttl)
        print(f"Log: Added {key} to redis")
    except Exception as e:
        print(f"Log: Redis_error {e}")

        
async def get_cache(key:str,redis_client:redis):
    try:
        cache = await redis_client.get(key)
        if cache is None:
            return None
        print("Log: Fetching from Redis")
        return json.loads(cache)
    
    except Exception as e:
        print(f"Log: Redis_error {e}")
