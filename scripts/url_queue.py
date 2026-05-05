import redis
import time
import json
import logging
from urllib.parse import urlparse
from collections import defaultdict

logger = logging.getLogger(__name__)

class URLQueue:
    """Distributed URL queue with priority management"""
    
    def __init__(self, redis_client):
        self.r = redis_client
        self.queues = {
            'high': 'url_queue:high',
            'medium': 'url_queue:medium', 
            'low': 'url_queue:low'
        }
        self.stats_key = 'queue_stats'
        self.domain_queues = 'domain_queues'
    
    def add_url(self, url, priority=50, metadata=None):
        """Add URL to appropriate priority queue"""
        # Validate URL
        if not url or not url.startswith(('http://', 'https://')):
            logger.warning(f"Invalid URL: {url}")
            return False
        
        # Check if already in queue
        if self.is_in_queue(url):
            logger.info(f"URL already in queue: {url}")
            return False
        
        # Determine priority queue
        queue_name = self._get_priority_queue(priority)
        
        # Prepare URL data
        url_data = {
            'url': url,
            'priority': priority,
            'added_time': time.time(),
            'metadata': metadata or {}
        }
        
        # Add to queue
        self.r.zadd(queue_name, {json.dumps(url_data): priority})
        
        # Add to domain-specific queue for rate limiting
        domain = urlparse(url).netloc
        self.r.zadd(f"{self.domain_queues}:{domain}", {url: priority})
        
        # Update stats
        self._update_stats('added')
        
        logger.info(f"Added to queue: {url} (priority: {priority})")
        return True
    
    def get_next_url(self):
        """Get next URL from highest priority queue"""
        # Check queues in priority order
        for queue_name in [self.queues['high'], self.queues['medium'], self.queues['low']]:
            item = self.r.zpopmin(queue_name)
            
            if item:
                url_data = json.loads(item[0][0])
                url = url_data['url']
                
                # Remove from domain queue
                domain = urlparse(url).netloc
                self.r.zrem(f"{self.domain_queues}:{domain}", url)
                
                # Update stats
                self._update_stats('processed')
                
                logger.info(f"Retrieved from queue: {url}")
                return url_data
        
        return None
    
    def is_in_queue(self, url):
        """Check if URL is already in any queue"""
        for queue_name in self.queues.values():
            items = self.r.zrange(queue_name, 0, -1)
            for item in items:
                url_data = json.loads(item)
                if url_data['url'] == url:
                    return True
        return False
    
    def _get_priority_queue(self, priority):
        """Determine which priority queue to use"""
        if priority <= 30:
            return self.queues['high']
        elif priority <= 70:
            return self.queues['medium']
        else:
            return self.queues['low']
    
    def _update_stats(self, operation):
        """Update queue statistics"""
        current_time = int(time.time())
        self.r.hincrby(self.stats_key, f"{operation}_{current_time}", 1)
    
    def get_queue_size(self):
        """Get total number of URLs in all queues"""
        total = 0
        for queue_name in self.queues.values():
            total += self.r.zcard(queue_name)
        return total
    
    def get_queue_stats(self):
        """Get detailed queue statistics"""
        stats = {
            'total_urls': self.get_queue_size(),
            'high_priority': self.r.zcard(self.queues['high']),
            'medium_priority': self.r.zcard(self.queues['medium']),
            'low_priority': self.r.zcard(self.queues['low']),
            'domain_queues': {}
        }
        
        # Get domain-specific stats
        for key in self.r.scan_iter(match=f"{self.domain_queues}:*"):
            domain = key.decode('utf-8').split(':')[-1]
            stats['domain_queues'][domain] = self.r.zcard(key)
        
        return stats
    
    def clear_queue(self):
        """Clear all queues"""
        for queue_name in self.queues.values():
            self.r.delete(queue_name)
        
        # Clear domain queues
        for key in self.r.scan_iter(match=f"{self.domain_queues}:*"):
            self.r.delete(key)
        
        self.r.delete(self.stats_key)
        logger.info("All queues cleared")


class PriorityCalculator:
    """Calculate URL priority based on various factors"""
    
    def __init__(self):
        self.domain_weights = {
            'wikipedia.org': 10,
            'github.com': 15,
            'stackoverflow.com': 20,
            'medium.com': 25,
            'arxiv.org': 5
        }
        
        self.keyword_weights = {
            # High priority keywords
            'tutorial': -10,
            'guide': -10,
            'documentation': -10,
            'api': -15,
            'official': -15,
            
            # Medium priority keywords
            'blog': 0,
            'article': 0,
            'news': 5,
            'update': 5,
            
            # Low priority keywords
            'advertisement': 20,
            'spam': 30,
            'promotion': 20
        }
    
    def calculate_priority(self, url, title="", content=""):
        """Calculate priority score for a URL"""
        base_score = 50  # Default medium priority
        
        # Domain-based priority
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        for domain_pattern, weight in self.domain_weights.items():
            if domain_pattern in domain:
                base_score += weight
                break
        
        # Keyword-based priority
        text = (title + " " + content).lower()
        
        for keyword, weight in self.keyword_weights.items():
            if keyword in text:
                base_score += weight
        
        # URL depth penalty
        path_depth = len([p for p in parsed_url.path.split('/') if p])
        if path_depth > 3:
            base_score += (path_depth - 3) * 5
        
        # File type considerations
        if parsed_url.path.endswith(('.pdf', '.doc', '.xls')):
            base_score += 10  # Slightly lower priority for documents
        
        # Clamp between 0 and 100
        priority = max(0, min(100, base_score))
        
        return priority
    
    def calculate_batch_priority(self, urls_data):
        """Calculate priority for multiple URLs"""
        results = []
        
        for url_data in urls_data:
            url = url_data['url']
            title = url_data.get('title', '')
            content = url_data.get('content', '')
            
            priority = self.calculate_priority(url, title, content)
            url_data['priority'] = priority
            results.append(url_data)
        
        return results


class QueueManager:
    """High-level queue management interface"""
    
    def __init__(self, redis_client):
        self.r = redis_client
        self.url_queue = URLQueue(redis_client)
        self.priority_calculator = PriorityCalculator()
    
    def add_urls_from_page(self, crawled_page):
        """Add URLs discovered from a crawled page"""
        if not crawled_page or 'links' not in crawled_page:
            return 0
        
        added_count = 0
        
        for link_data in crawled_page['links']:
            url = link_data['url']
            
            # Calculate priority based on context
            priority = self.priority_calculator.calculate_priority(
                url, 
                crawled_page.get('title', ''),
                crawled_page.get('content', '')
            )
            
            # Prepare metadata
            metadata = {
                'source_url': crawled_page['url'],
                'anchor_text': link_data['anchor_text'],
                'discovered_time': time.time()
            }
            
            # Add to queue
            if self.url_queue.add_url(url, priority, metadata):
                added_count += 1
        
        logger.info(f"Added {added_count} new URLs to queue from {crawled_page['url']}")
        return added_count
    
    def get_next_batch(self, batch_size=10):
        """Get next batch of URLs to crawl"""
        urls = []
        
        for _ in range(batch_size):
            url_data = self.url_queue.get_next_url()
            if url_data:
                urls.append(url_data)
            else:
                break
        
        return urls
    
    def get_dashboard_stats(self):
        """Get comprehensive statistics for dashboard"""
        queue_stats = self.url_queue.get_queue_stats()
        
        return {
            'queue': queue_stats,
            'timestamp': time.time(),
            'total_processed': sum(int(v) for v in self.r.hgetall('queue_stats').values()),
            'domains_active': len([k for k in self.r.scan_iter(match="domain_queues:*")])
        }
