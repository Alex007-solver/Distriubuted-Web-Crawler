import logging
import time
import json
import redis
from datetime import datetime
from typing import Dict, List, Optional
import sys

class CrawlerLogger:
    """Enhanced logging system for the distributed crawler"""
    
    def __init__(self, redis_client, config=None):
        self.r = redis_client
        self.config = config or {}
        
        # Setup console logging
        self.setup_console_logging()
        
        # Redis keys for logging
        self.log_key = "crawler_logs"
        self.stats_key = "crawler_stats"
        self.errors_key = "crawler_errors"
        self.performance_key = "crawler_performance"
        
        # In-memory buffer for batch logging
        self.log_buffer = []
        self.buffer_size = 100
        self.last_flush = time.time()
        self.flush_interval = 30  # seconds
    
    def setup_console_logging(self):
        """Setup console logging with proper formatting"""
        level = self.config.get('level', 'INFO')
        log_format = self.config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        logging.basicConfig(
            level=getattr(logging, level.upper()),
            format=log_format,
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger('DistributedCrawler')
    
    def log_event(self, event_type: str, message: str, data: Dict = None):
        """Log an event with structured data"""
        log_entry = {
            'timestamp': time.time(),
            'datetime': datetime.now().isoformat(),
            'event_type': event_type,
            'message': message,
            'data': data or {}
        }
        
        # Add to buffer
        self.log_buffer.append(log_entry)
        
        # Log to console
        level = getattr(logging, self._get_log_level(event_type))
        self.logger.log(level, f"[{event_type}] {message}")
        
        # Flush buffer if needed
        if len(self.log_buffer) >= self.buffer_size or time.time() - self.last_flush > self.flush_interval:
            self.flush_logs()
    
    def _get_log_level(self, event_type: str) -> str:
        """Determine log level based on event type"""
        if event_type in ['ERROR', 'CRITICAL']:
            return 'ERROR'
        elif event_type in ['WARNING']:
            return 'WARNING'
        elif event_type in ['DEBUG']:
            return 'DEBUG'
        else:
            return 'INFO'
    
    def flush_logs(self):
        """Flush log buffer to Redis"""
        if not self.log_buffer:
            return
        
        try:
            # Add to Redis list (keep last 10000 entries)
            pipe = self.r.pipeline()
            for log_entry in self.log_buffer:
                pipe.lpush(self.log_key, json.dumps(log_entry))
            pipe.ltrim(self.log_key, 0, 9999)
            pipe.execute()
            
            self.log_buffer.clear()
            self.last_flush = time.time()
            
        except Exception as e:
            self.logger.error(f"Error flushing logs to Redis: {e}")
    
    def log_crawl_start(self, url: str, worker_id: str):
        """Log when crawling starts for a URL"""
        self.log_event('CRAWL_START', f"Started crawling: {url}", {
            'url': url,
            'worker_id': worker_id
        })
    
    def log_crawl_success(self, url: str, worker_id: str, stats: Dict):
        """Log successful crawl"""
        self.log_event('CRAWL_SUCCESS', f"Successfully crawled: {url}", {
            'url': url,
            'worker_id': worker_id,
            'stats': stats
        })
        
        # Update statistics
        self._update_stats('pages_crawled', 1)
        self._update_stats('total_content_size', stats.get('content_length', 0))
    
    def log_crawl_error(self, url: str, worker_id: str, error: str):
        """Log crawl error"""
        self.log_event('CRAWL_ERROR', f"Error crawling {url}: {error}", {
            'url': url,
            'worker_id': worker_id,
            'error': error
        })
        
        # Track errors
        error_data = {
            'timestamp': time.time(),
            'url': url,
            'worker_id': worker_id,
            'error': error
        }
        self.r.lpush(self.errors_key, json.dumps(error_data))
        self.r.ltrim(self.errors_key, 0, 999)
        
        # Update statistics
        self._update_stats('errors', 1)
    
    def log_queue_event(self, event_type: str, url: str, priority: int = None):
        """Log queue-related events"""
        data = {'url': url}
        if priority is not None:
            data['priority'] = priority
        
        self.log_event(event_type, f"Queue {event_type}: {url}", data)
    
    def log_worker_event(self, worker_id: str, event_type: str, message: str):
        """Log worker-specific events"""
        self.log_event(f'WORKER_{event_type}', f"Worker {worker_id}: {message}", {
            'worker_id': worker_id
        })
    
    def log_performance(self, operation: str, duration: float, details: Dict = None):
        """Log performance metrics"""
        perf_data = {
            'timestamp': time.time(),
            'operation': operation,
            'duration': duration,
            'details': details or {}
        }
        
        self.r.lpush(self.performance_key, json.dumps(perf_data))
        self.r.ltrim(self.performance_key, 0, 9999)
        
        # Update performance stats
        self._update_performance_stats(operation, duration)
    
    def _update_stats(self, stat_name: str, value: int):
        """Update crawler statistics"""
        self.r.hincrby(self.stats_key, stat_name, value)
        self.r.hset(self.stats_key, 'last_updated', time.time())
    
    def _update_performance_stats(self, operation: str, duration: float):
        """Update performance statistics"""
        key = f"perf:{operation}"
        
        # Update average, min, max
        pipe = self.r.pipeline()
        pipe.hincrby(key, 'count', 1)
        pipe.hincrbyfloat(key, 'total_duration', duration)
        pipe.hincrbyfloat(key, 'min_duration', duration)
        pipe.hincrbyfloat(key, 'max_duration', duration)
        pipe.execute()
        
        # Calculate new average
        stats = self.r.hgetall(key)
        count = int(stats.get('count', 0))
        total = float(stats.get('total_duration', 0))
        avg = total / count if count > 0 else 0
        
        self.r.hset(key, 'avg_duration', avg)
    
    def get_stats(self) -> Dict:
        """Get comprehensive crawler statistics"""
        stats = self.r.hgetall(self.stats_key)
        
        # Convert bytes to strings and parse numbers
        parsed_stats = {}
        for key, value in stats.items():
            key_str = key.decode('utf-8') if isinstance(key, bytes) else key
            value_str = value.decode('utf-8') if isinstance(value, bytes) else value
            
            try:
                # Try to parse as number
                if '.' in value_str:
                    parsed_stats[key_str] = float(value_str)
                else:
                    parsed_stats[key_str] = int(value_str)
            except ValueError:
                parsed_stats[key_str] = value_str
        
        return parsed_stats
    
    def get_recent_logs(self, limit: int = 50) -> List[Dict]:
        """Get recent log entries"""
        logs = self.r.lrange(self.log_key, 0, limit - 1)
        
        parsed_logs = []
        for log in logs:
            try:
                log_str = log.decode('utf-8') if isinstance(log, bytes) else log
                parsed_logs.append(json.loads(log_str))
            except json.JSONDecodeError:
                continue
        
        return parsed_logs
    
    def get_recent_errors(self, limit: int = 20) -> List[Dict]:
        """Get recent error entries"""
        errors = self.r.lrange(self.errors_key, 0, limit - 1)
        
        parsed_errors = []
        for error in errors:
            try:
                error_str = error.decode('utf-8') if isinstance(error, bytes) else error
                parsed_errors.append(json.loads(error_str))
            except json.JSONDecodeError:
                continue
        
        return parsed_errors
    
    def get_performance_stats(self) -> Dict:
        """Get performance statistics"""
        perf_keys = self.r.keys('perf:*')
        
        perf_stats = {}
        for key in perf_keys:
            key_str = key.decode('utf-8') if isinstance(key, bytes) else key
            operation = key_str.replace('perf:', '')
            
            stats = self.r.hgetall(key)
            parsed_stats = {}
            
            for stat_key, stat_value in stats.items():
                stat_key_str = stat_key.decode('utf-8') if isinstance(stat_key, bytes) else stat_key
                stat_value_str = stat_value.decode('utf-8') if isinstance(stat_value, bytes) else stat_value
                
                try:
                    if '.' in stat_value_str:
                        parsed_stats[stat_key_str] = float(stat_value_str)
                    else:
                        parsed_stats[stat_key_str] = int(stat_value_str)
                except ValueError:
                    parsed_stats[stat_key_str] = stat_value_str
            
            perf_stats[operation] = parsed_stats
        
        return perf_stats
    
    def generate_report(self) -> Dict:
        """Generate comprehensive report"""
        return {
            'timestamp': time.time(),
            'stats': self.get_stats(),
            'recent_errors': self.get_recent_errors(10),
            'performance': self.get_performance_stats(),
            'queue_size': self._get_queue_size()
        }
    
    def _get_queue_size(self) -> int:
        """Get total queue size"""
        queue_keys = self.r.keys('url_queue:*')
        total_size = 0
        
        for key in queue_keys:
            total_size += self.r.zcard(key)
        
        return total_size
    
    def cleanup_old_logs(self, days: int = 7):
        """Clean up old log entries"""
        cutoff_time = time.time() - (days * 24 * 3600)
        
        # This would require more complex logic to selectively remove old entries
        # For now, we just trim the lists to keep them manageable
        self.r.ltrim(self.log_key, 0, 10000)
        self.r.ltrim(self.errors_key, 0, 1000)
        self.r.ltrim(self.performance_key, 0, 5000)


# Global logger instance (will be initialized in main)
_logger_instance = None

def init_logger(redis_client, config=None):
    """Initialize global logger instance"""
    global _logger_instance
    _logger_instance = CrawlerLogger(redis_client, config)
    return _logger_instance

def get_logger() -> Optional[CrawlerLogger]:
    """Get global logger instance"""
    return _logger_instance
