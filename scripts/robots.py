import requests
import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
import redis
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RobotsCache:
    """Cache for robots.txt files with expiration"""
    
    def __init__(self, redis_client):
        self.r = redis_client
        self.default_delay = 1.0  # Default 1 second delay
        self.cache_duration = 86400  # 24 hours cache duration
    
    def get_robots_parser(self, url):
        """Get RobotFileParser for a URL, using cache when possible"""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        # Check cache first
        cached_data = self.r.hgetall(f"robots:{domain}")
        
        if cached_data:
            # Check if cache is still valid
            expires_at = float(cached_data.get(b'expires_at', 0))
            if expires_at > time.time():
                # Return cached parser
                parser = RobotFileParser()
                parser.set_url(f"https://{domain}/robots.txt")
                parser.read()  # This will use cached content
                content = cached_data.get(b'content', b'').decode('utf-8')
                if content:
                    parser.parse(content.splitlines())
                return parser
            else:
                # Cache expired, remove it
                self.r.delete(f"robots:{domain}")
        
        # Fetch fresh robots.txt
        return self._fetch_robots_txt(domain)
    
    def _fetch_robots_txt(self, domain):
        """Fetch and parse robots.txt for a domain"""
        robots_url = f"https://{domain}/robots.txt"
        
        try:
            response = requests.get(robots_url, timeout=10, headers={
                'User-Agent': 'DistributedCrawler/1.0 (educational project)'
            })
            
            if response.status_code == 200:
                content = response.text
                parser = RobotFileParser()
                parser.set_url(robots_url)
                parser.parse(content.splitlines())
                
                # Cache the result
                expires_at = time.time() + self.cache_duration
                self.r.hset(f"robots:{domain}", mapping={
                    'content': content,
                    'expires_at': str(expires_at)
                })
                
                logger.info(f"Cached robots.txt for {domain}")
                return parser
            else:
                logger.warning(f"No robots.txt found for {domain} (status: {response.status_code})")
                
        except Exception as e:
            logger.error(f"Error fetching robots.txt for {domain}: {e}")
        
        # Return a permissive parser if robots.txt is not available
        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.allow_all = True
        return parser
    
    def can_fetch(self, url, user_agent='*'):
        """Check if URL can be fetched according to robots.txt"""
        parser = self.get_robots_parser(url)
        return parser.can_fetch(user_agent, url)
    
    def get_crawl_delay(self, url, user_agent='*'):
        """Get crawl delay for a URL"""
        parser = self.get_robots_parser(url)
        delay = parser.crawl_delay(user_agent)
        return delay if delay is not None else self.default_delay


class RateLimiter:
    """Distributed rate limiter using Redis"""
    
    def __init__(self, redis_client):
        self.r = redis_client
    
    def acquire(self, domain, delay=1.0):
        """Acquire permission to crawl a domain, respecting delay"""
        key = f"rate_limit:{domain}"
        
        while True:
            now = time.time()
            last_request = self.r.get(key)
            
            if last_request is None:
                # First request for this domain
                self.r.set(key, now)
                return
            
            elapsed = now - float(last_request)
            
            if elapsed >= delay:
                # Enough time has passed
                self.r.set(key, now)
                return
            
            # Wait for the remaining time
            sleep_time = delay - elapsed
            logger.info(f"Rate limiting {domain}: waiting {sleep_time:.2f}s")
            time.sleep(sleep_time)


def check_robots_and_wait(url, redis_client, user_agent='*'):
    """Combined function to check robots.txt and respect rate limiting"""
    robots_cache = RobotsCache(redis_client)
    rate_limiter = RateLimiter(redis_client)
    
    # Check if URL is allowed
    if not robots_cache.can_fetch(url, user_agent):
        logger.warning(f"URL blocked by robots.txt: {url}")
        return False
    
    # Get appropriate crawl delay and wait
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    delay = robots_cache.get_crawl_delay(url, user_agent)
    
    rate_limiter.acquire(domain, delay)
    
    return True
