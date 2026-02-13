
import json
import redis.asyncio as redis
from src.config import settings
from src.logger import error
from src.external.account_service import account_service

class QuotaService:
    def __init__(self):
        self.redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )
        self.CACHE_TTL = 3600 # 1 hour cache for plan details

    async def _get_plan_details(self, profile_id: str):
        # 1. Check Redis Cache
        cache_key = f"plan_details:{profile_id}"
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)

        # 2. Fetch from Account Service
        details = await account_service.get_plan_details(profile_id)
        if details:
            await self.redis.setex(cache_key, self.CACHE_TTL, json.dumps(details))
        
        return details

    async def check_feature(self, profile_id: str, feature_code: str) -> bool:
        details = await self._get_plan_details(profile_id)
        if not details:
            return False # Fail safe: deny if no plan info
            
        features = details.get("features", {})
        return features.get(feature_code, False)

quota_service = QuotaService()
