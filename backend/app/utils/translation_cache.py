# backend/app/utils/translation_cache.py
from typing import Optional, Dict
from datetime import datetime, timedelta
from app.config.database import translations_cache, redis_client
import json
import hashlib
import logging

logger = logging.getLogger(__name__)

class TranslationCache:
    def __init__(self):
        self.cache_duration = timedelta(days=7)  # Cache translations for 7 days
        self.redis_prefix = "translation:"

    def _generate_cache_key(
        self,
        text: str,
        source_lang: str,
        target_lang: str
    ) -> str:
        """Generate a unique cache key."""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        return f"{self.redis_prefix}{source_lang}:{target_lang}:{text_hash}"

    async def get_cached_translation(
        self,
        text: str,
        source_lang: str,
        target_lang: str
    ) -> Optional[str]:
        """Get translation from cache."""
        try:
            # First check Redis for faster access
            cache_key = self._generate_cache_key(text, source_lang, target_lang)
            cached_data = redis_client.get(cache_key)

            if cached_data:
                logger.debug(f"Translation found in Redis cache: {cache_key}")
                return json.loads(cached_data)["translated_text"]

            # If not in Redis, check MongoDB
            result = await translations_cache.find_one({
                "source_text": text,
                "source_language": source_lang,
                "target_language": target_lang,
                "created_at": {"$gte": datetime.utcnow() - self.cache_duration}
            })

            if result:
                logger.debug("Translation found in MongoDB cache")
                # Update Redis cache
                self._update_redis_cache(
                    cache_key,
                    result["translated_text"],
                    source_lang,
                    target_lang
                )
                return result["translated_text"]

            return None

        except Exception as e:
            logger.error(f"Error retrieving cached translation: {str(e)}")
            return None

    async def cache_translation(
        self,
        text: str,
        translated_text: str,
        source_lang: str,
        target_lang: str,
        metadata: Optional[Dict] = None
    ):
        """Cache translation in both Redis and MongoDB."""
        try:
            cache_key = self._generate_cache_key(text, source_lang, target_lang)
            timestamp = datetime.utcnow()

            # Cache in Redis
            cache_data = {
                "translated_text": translated_text,
                "source_language": source_lang,
                "target_language": target_lang,
                "timestamp": timestamp.isoformat(),
                "metadata": metadata or {}
            }
            redis_client.setex(
                cache_key,
                int(self.cache_duration.total_seconds()),
                json.dumps(cache_data)
            )

            # Cache in MongoDB
            await translations_cache.update_one(
                {
                    "source_text": text,
                    "source_language": source_lang,
                    "target_language": target_lang
                },
                {
                    "$set": {
                        "translated_text": translated_text,
                        "created_at": timestamp,
                        "metadata": metadata or {},
                        "cache_key": cache_key
                    }
                },
                upsert=True
            )

            logger.debug(f"Translation cached successfully: {cache_key}")

        except Exception as e:
            logger.error(f"Error caching translation: {str(e)}")

    def _update_redis_cache(
        self,
        cache_key: str,
        translated_text: str,
        source_lang: str,
        target_lang: str
    ):
        """Update Redis cache with translation."""
        try:
            cache_data = {
                "translated_text": translated_text,
                "source_language": source_lang,
                "target_language": target_lang,
                "timestamp": datetime.utcnow().isoformat()
            }
            redis_client.setex(
                cache_key,
                int(self.cache_duration.total_seconds()),
                json.dumps(cache_data)
            )
        except Exception as e:
            logger.error(f"Error updating Redis cache: {str(e)}")

    async def clear_expired_cache(self):
        """Clear expired translations from MongoDB."""
        try:
            expiry_date = datetime.utcnow() - self.cache_duration
            result = await translations_cache.delete_many({
                "created_at": {"$lt": expiry_date}
            })
            logger.info(f"Cleared {result.deleted_count} expired translations from cache")
        except Exception as e:
            logger.error(f"Error clearing expired cache: {str(e)}")