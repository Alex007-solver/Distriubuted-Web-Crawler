#!/usr/bin/env python3
"""
Distributed Web Crawler - Main Orchestrator
A comprehensive distributed web crawler with advanced features including:
- Distributed architecture with multiple workers
- URL queue management with priority system
- Duplicate detection using bloom filters
- Robots.txt compliance and rate limiting
- Structured data extraction and storage
- Real-time monitoring and logging
"""

import sys
import time
import signal
import argparse
import threading
import subprocess
from pathlib import Path

# Add scripts directory to path
sys.path.append(str(Path(__file__).parent / "scripts"))

import redis
from config import ConfigManager, get_config
from logger import init_logger, get_logger
from url_queue import QueueManager
from general_crawler import GeneralWebCrawler
from scripts.producer import main as arxiv_producer_main
from scripts.worker import main as arxiv_worker_main
from scripts.db import get_connection

class DistributedCrawler:
    """Main distributed crawler orchestrator"""
    
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
        
        # Initialize components
        self.queue_manager = QueueManager(self.redis_client)
        self.crawler = GeneralWebCrawler(self.redis_client, self.config.crawler.__dict__)
        
        # Worker management
        self.workers = []
        self.running = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        print("✓ Distributed crawler initialized")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\nReceived signal {signum}, shutting down...")
        self.shutdown()
        sys.exit(0)
    
    def add_seed_urls(self, urls):
        """Add seed URLs to start crawling"""
        added_count = 0
        
        for url in urls:
            priority = self.config_manager.calculate_priority(url, url)
            if self.queue_manager.url_queue.add_url(url, priority):
                added_count += 1
        
        print(f"✓ Added {added_count} seed URLs to queue")
        return added_count
    
    def start_workers(self, num_workers=None):
        """Start crawler worker processes"""
        num_workers = num_workers or self.config.crawler.max_workers
        print(f"Starting {num_workers} worker processes...")
        
        # Set crawler running flag
        self.redis_client.set('crawler_running', '1')
        
        for i in range(num_workers):
            worker_script = Path(__file__).parent / "scripts" / "standalone_worker.py"
            cmd = [sys.executable, str(worker_script), str(i)]
            
            if self.config_manager.config_file:
                cmd.extend(['--config', self.config_manager.config_file])
            
            worker = subprocess.Popen(cmd)
            self.workers.append(worker)
            print(f"✓ Started worker {i}")
        
        self.running = True
        print(f"✓ All {num_workers} workers started")
    
    
    
    def start_arxiv_crawler(self):
        """Start the arXiv-specific crawler (legacy functionality)"""
        print("Starting arXiv crawler...")
        
        # Start arXiv producer in separate thread
        producer_thread = threading.Thread(
            target=arxiv_producer_main,
            name="ArxivProducer"
        )
        producer_thread.start()
        
        # Start arXiv workers
        arxiv_workers = []
        for i in range(2):  # 2 arXiv workers
            worker = multiprocessing.Process(
                target=arxiv_worker_main,
                name=f"ArxivWorker-{i}"
            )
            worker.start()
            arxiv_workers.append(worker)
        
        return producer_thread, arxiv_workers
    
    def monitor_system(self):
        """System monitoring dashboard"""
        while self.running:
            try:
                stats = self.queue_manager.get_dashboard_stats()
                logger_stats = get_logger().get_stats()
                
                print("\n" + "="*60)
                print("DISTRIBUTED CRAWLER DASHBOARD")
                print("="*60)
                print(f"Active Workers: {len(self.workers)}")
                print(f"Queue Size: {stats['queue']['total_urls']}")
                print(f"  - High Priority: {stats['queue']['high_priority']}")
                print(f"  - Medium Priority: {stats['queue']['medium_priority']}")
                print(f"  - Low Priority: {stats['queue']['low_priority']}")
                print(f"Pages Crawled: {logger_stats.get('pages_crawled', 0)}")
                print(f"Errors: {logger_stats.get('errors', 0)}")
                print(f"Active Domains: {stats['domains_active']}")
                print("="*60)
                
                time.sleep(30)  # Update every 30 seconds
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Monitor error: {e}")
                time.sleep(10)
    
    def shutdown(self):
        """Graceful shutdown"""
        print("Shutting down distributed crawler...")
        self.running = False
        
        # Signal workers to stop
        self.redis_client.delete('crawler_running')
        
        # Wait for workers to finish
        for worker in self.workers:
            try:
                worker.wait(timeout=10)
            except subprocess.TimeoutExpired:
                worker.terminate()
                worker.wait()
        
        # Flush logs
        if get_logger():
            get_logger().flush_logs()
        
        print("✓ Shutdown complete")
    
    def run(self, seed_urls=None, num_workers=None, enable_monitoring=True):
        """Main run method"""
        print("Starting distributed web crawler...")
        
        # Add seed URLs
        if seed_urls:
            self.add_seed_urls(seed_urls)
        else:
            # Default seed URLs
            default_seeds = [
                'https://en.wikipedia.org/wiki/Artificial_intelligence',
                'https://github.com/topics/machine-learning',
                'https://arxiv.org/list/cs/recent'
            ]
            self.add_seed_urls(default_seeds)
        
        # Start workers
        self.start_workers(num_workers)
        
        # Start monitoring if enabled
        if enable_monitoring:
            monitor_thread = threading.Thread(target=self.monitor_system, daemon=True)
            monitor_thread.start()
        
        try:
            # Keep main thread alive
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutdown requested...")
        finally:
            self.shutdown()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Distributed Web Crawler')
    parser.add_argument('--config', '-c', help='Configuration file path')
    parser.add_argument('--workers', '-w', type=int, help='Number of worker processes')
    parser.add_argument('--seeds', '-s', nargs='+', help='Seed URLs to start crawling')
    parser.add_argument('--arxiv', action='store_true', help='Run arXiv crawler only')
    parser.add_argument('--no-monitor', action='store_true', help='Disable monitoring dashboard')
    parser.add_argument('--setup-db', action='store_true', help='Setup database schema')
    
    args = parser.parse_args()
    
    # Setup database if requested
    if args.setup_db:
        print("Setting up database schema...")
        print("Please run: mysql -u root -p < schema.sql")
        return
    
    # Initialize crawler
    crawler = DistributedCrawler(args.config)
    
    if args.arxiv:
        # Run arXiv crawler only
        producer_thread, arxiv_workers = crawler.start_arxiv_crawler()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down arXiv crawler...")
    else:
        # Run general distributed crawler
        crawler.run(
            seed_urls=args.seeds,
            num_workers=args.workers,
            enable_monitoring=not args.no_monitor
        )


if __name__ == "__main__":
    main()
