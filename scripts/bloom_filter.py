import redis
import hashlib
from pybloom_live import BloomFilter
import pickle
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class DistributedBloomFilter:
    """Distributed bloom filter using Redis for efficient duplicate detection"""
    
    def __init__(self, redis_client, capacity=1000000, error_rate=0.001):
        # Create a separate Redis client for binary data (no decode_responses)
        self.r_binary = redis.Redis(
            host=redis_client.connection_pool.connection_kwargs.get('host', 'localhost'),
            port=redis_client.connection_pool.connection_kwargs.get('port', 6379),
            db=redis_client.connection_pool.connection_kwargs.get('db', 0),
            password=redis_client.connection_pool.connection_kwargs.get('password'),
            decode_responses=False  # Keep binary data for pickle
        )
        self.capacity = capacity
        self.error_rate = error_rate
        self.local_filter = None
        self.redis_key = "bloom_filter:urls"
        self._load_or_create_filter()
    
    def _load_or_create_filter(self):
        """Load existing bloom filter from Redis or create new one"""
        try:
            # Try to load from Redis (binary client)
            filter_data = self.r_binary.get(self.redis_key)
            if filter_data:
                self.local_filter = pickle.loads(filter_data)
                logger.info(f"Loaded bloom filter from Redis with {self.capacity} capacity")
            else:
                # Create new filter
                self.local_filter = BloomFilter(capacity=self.capacity, error_rate=self.error_rate)
                logger.info(f"Created new bloom filter with {self.capacity} capacity")
        except Exception as e:
            logger.error(f"Error loading bloom filter: {e}")
            # Create new filter as fallback
            self.local_filter = BloomFilter(capacity=self.capacity, error_rate=self.error_rate)
    
    def _save_to_redis(self):
        """Save bloom filter to Redis"""
        try:
            filter_data = pickle.dumps(self.local_filter)
            self.r_binary.set(self.redis_key, filter_data)
        except Exception as e:
            logger.error(f"Error saving bloom filter to Redis: {e}")
    
    def add(self, url):
        """Add URL to bloom filter"""
        if url not in self.local_filter:
            self.local_filter.add(url)
            self._save_to_redis()
            return True
        return False
    
    def __contains__(self, url):
        """Check if URL might be in the filter"""
        return url in self.local_filter
    
    def add_batch(self, urls):
        """Add multiple URLs to bloom filter"""
        new_urls = []
        for url in urls:
            if url not in self.local_filter:
                self.local_filter.add(url)
                new_urls.append(url)
        
        if new_urls:
            self._save_to_redis()
        
        return new_urls
    
    def get_stats(self):
        """Get bloom filter statistics"""
        return {
            'capacity': self.capacity,
            'error_rate': self.error_rate,
            'current_size': len(self.local_filter)
        }


class URLHasher:
    """Utility class for consistent URL hashing"""
    
    @staticmethod
    def normalize_url(url):
        """Normalize URL for consistent hashing"""
        from urllib.parse import urlparse, urlunparse
        
        parsed = urlparse(url.lower())
        
        # Remove fragment and normalize
        normalized = parsed._replace(
            fragment='',
            path=parsed.path.rstrip('/') or '/'
        )
        
        return urlunparse(normalized)
    
    @staticmethod
    def hash_url(url):
        """Generate SHA-256 hash for URL"""
        normalized = URLHasher.normalize_url(url)
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
    
    @staticmethod
    def domain_hash(url):
        """Generate hash for domain only"""
        parsed = urlparse(url.lower())
        return hashlib.sha256(parsed.netloc.encode('utf-8')).hexdigest()


class DuplicateDetector:
    """Advanced duplicate detection using multiple strategies"""
    
    def __init__(self, redis_client):
        self.r = redis_client
        self.bloom_filter = DistributedBloomFilter(redis_client)
        self.url_hasher = URLHasher()
        
        # Redis sets for exact tracking (smaller, more accurate)
        self.seen_urls_key = "seen_urls"
        self.seen_hashes_key = "seen_hashes"
    
    def is_duplicate(self, url):
        """Check if URL is a duplicate using multiple strategies"""
        normalized_url = self.url_hasher.normalize_url(url)
        url_hash = self.url_hasher.hash_url(url)
        
        # Check bloom filter first (fast, probabilistic)
        if normalized_url in self.bloom_filter:
            # Double-check with exact Redis set
            if self.r.sismember(self.seen_urls_key, normalized_url):
                return True
        
        # Check content hash (for identical content detection)
        if self.r.sismember(self.seen_hashes_key, url_hash):
            return True
        
        return False
    
    def mark_seen(self, url, content_hash=None):
        """Mark URL as seen"""
        normalized_url = self.url_hasher.normalize_url(url)
        url_hash = self.url_hasher.hash_url(url)
        
        # Add to bloom filter
        self.bloom_filter.add(normalized_url)
        
        # Add to exact tracking sets
        self.r.sadd(self.seen_urls_key, normalized_url)
        self.r.sadd(self.seen_hashes_key, url_hash)
        
        # Store content hash if provided
        if content_hash:
            self.r.hset("content_hashes", normalized_url, content_hash)
    
    def get_duplicate_stats(self):
        """Get statistics about duplicate detection"""
        bloom_stats = self.bloom_filter.get_stats()
        
        return {
            'bloom_filter': bloom_stats,
            'exact_urls_seen': self.r.scard(self.seen_urls_key),
            'exact_hashes_seen': self.r.scard(self.seen_hashes_key),
            'content_hashes_stored': self.r.hlen("content_hashes")
        }
    
    def cleanup_old_entries(self, days_old=30):
        """Clean up old entries to prevent memory bloat"""
        # This is a placeholder for cleanup logic
        # In practice, you might want to implement time-based expiration
        logger.info("Cleanup not implemented - consider using Redis TTL for automatic cleanup")
