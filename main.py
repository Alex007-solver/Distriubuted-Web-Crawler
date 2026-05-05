#!/usr/bin/env python3
"""
Distributed Web Crawler - Main Orchestrator (Refactored for Celery)
A comprehensive distributed web crawler that uses Celery for task distribution.
This version acts strictly as a producer, submitting tasks to Celery workers.
"""

import sys
import time
import signal
import argparse
from pathlib import Path

# Add scripts directory to path
sys.path.append(str(Path(__file__).parent / "scripts"))

import redis
from config import ConfigManager, get_config
from logger import init_logger, get_logger
from crawler_tasks import batch_crawl_task

class DistributedCrawler:
    """Main distributed crawler orchestrator using Celery"""
    
    def __init__(self, config_file=None):
        # Load configuration
        self.config_manager = ConfigManager(config_file) if config_file else ConfigManager()
        self.config = get_config()
        
        # Initialize Redis connection
        self.redis_client = redis.Redis(
            host=self.config.redis.host,
            port=self.config.redis.port,
            db=self.config.redis.db,
            password=self.config.redis.password,
            decode_responses=True
        )
        
        # Test Redis connection
        try:
            self.redis_client.ping()
            print("✓ Redis connection established")
        except redis.ConnectionError:
            print("✗ Failed to connect to Redis")
            sys.exit(1)
        
        # Initialize logger
        self.logger = init_logger(self.redis_client, self.config.logging.__dict__)
        print("✓ Logger initialized")
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        print("✓ Distributed crawler initialized (Celery-based)")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\nReceived signal {signum}, shutting down...")
        self.shutdown()
        sys.exit(0)
    
    def add_seed_urls(self, urls):
        """Add seed URLs to start crawling via Celery"""
        print(f"Submitting {len(urls)} seed URLs to Celery...")
        
        # Submit batch crawl task to Celery
        task_result = batch_crawl_task.delay(urls)
        
        print(f"✓ Submitted batch crawl task: {task_result.id}")
        print(f"✓ Task status: {task_result.status}")
        
        return task_result
    
    def monitor_celery_tasks(self):
        """Monitor Celery task progress"""
        print("Starting Celery task monitoring...")
        
        try:
            while True:
                # Get task statistics from Redis
                try:
                    # Celery stores task stats in Redis
                    stats = self.redis_client.hgetall('celery-stats')
                    if stats:
                        print(f"\nCelery Stats: {stats}")
                except:
                    pass
                
                # Check active tasks
                try:
                    active_tasks = self.redis_client.lrange('celery', 0, -1)
                    if active_tasks:
                        print(f"Active tasks in queue: {len(active_tasks)}")
                except:
                    pass
                
                time.sleep(30)  # Update every 30 seconds
                
        except KeyboardInterrupt:
            print("\nMonitoring stopped...")
    
    def shutdown(self):
        """Graceful shutdown"""
        print("Shutting down distributed crawler...")
        
        # Flush logs
        if get_logger():
            get_logger().flush_logs()
        
        print("✓ Shutdown complete")
    
    def run(self, seed_urls=None, enable_monitoring=True):
        """Main run method - acts as Celery producer"""
        print("Starting distributed web crawler (Celery producer)...")
        
        # Add seed URLs
        if seed_urls:
            self.add_seed_urls(seed_urls)
        else:
            # Default seed URLs
            default_seeds = [
                'https://en.wikipedia.org/wiki/Artificial_intelligence',
                'https://github.com/topics/machine-learning',
                'https://arxiv.org/list/cs/recent',
                'https://httpbin.org/html',
                'https://example.com'
            ]
            self.add_seed_urls(default_seeds)
        
        print("✓ URLs submitted to Celery for processing")
        print("✓ Make sure Celery workers are running: celery -A celery_app worker --loglevel=info")
        
        # Start monitoring if enabled
        if enable_monitoring:
            self.monitor_celery_tasks()
        else:
            print("Monitoring disabled. Check Celery worker logs for progress.")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Distributed Web Crawler (Celery-based)')
    parser.add_argument('--config', '-c', help='Configuration file path')
    parser.add_argument('--seeds', '-s', nargs='+', help='Seed URLs to start crawling')
    parser.add_argument('--no-monitor', action='store_true', help='Disable Celery task monitoring')
    parser.add_argument('--setup-db', action='store_true', help='Setup database schema')
    
    args = parser.parse_args()
    
    # Setup database if requested
    if args.setup_db:
        print("Setting up database schema...")
        print("Please run: mysql -u root -p < schema.sql")
        print("Then run: python -c \"from models import db_manager; db_manager.create_tables()\"")
        return
    
    # Initialize crawler
    crawler = DistributedCrawler(args.config)
    
    # Run general distributed crawler (Celery producer only)
    crawler.run(
        seed_urls=args.seeds,
        enable_monitoring=not args.no_monitor
    )


if __name__ == "__main__":
    main()
