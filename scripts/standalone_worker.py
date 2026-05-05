#!/usr/bin/env python3
"""
Standalone worker process for distributed web crawler
This script runs as a separate process to avoid pickling issues
"""

import sys
import time
import signal
import argparse
from pathlib import Path

# Add scripts directory to path
sys.path.append(str(Path(__file__).parent))

import redis
from config import ConfigManager
from logger import init_logger
from general_crawler import GeneralWebCrawler
from url_queue import QueueManager
from db import get_connection

class StandaloneWorker:
    """Standalone worker process"""
    
    def __init__(self, worker_id, config_file=None):
        self.worker_id = worker_id
        self.config_manager = ConfigManager(config_file) if config_file else ConfigManager()
        self.config = self.config_manager.config
        self.running = False
        
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
            print(f"Worker {worker_id}: Redis connection established")
        except redis.ConnectionError:
            print(f"Worker {worker_id}: Failed to connect to Redis")
            sys.exit(1)
        
        # Initialize components
        self.logger = init_logger(self.redis_client, self.config.logging.__dict__)
        self.crawler = GeneralWebCrawler(self.redis_client, self.config.crawler.__dict__)
        self.queue_manager = QueueManager(self.redis_client)
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"Worker {self.worker_id}: Received signal {signum}, shutting down...")
        self.running = False
    
    def _store_crawled_data(self, result):
        """Store crawled data in database using SQLAlchemy"""
        try:
            from db_sqlalchemy import (
                insert_paper, insert_keyword, link_paper_keyword,
                insert_stats, insert_discovered_link
            )
            
            # Prepare paper data for SQLAlchemy
            paper_data = {
                'url': result['url'],
                'title': result['title'],
                'content': result['content'],
                'content_hash': result['content_hash'],
                'domain': result['metadata']['domain'],
                'status': 'completed',
                'priority': 50,  # Default priority
                'crawl_date': result['crawl_date']
            }
            
            # Insert main paper
            paper_id = insert_paper(paper_data)
            
            if paper_id:
                # Insert keywords and link them
                for keyword in result['keywords']:
                    keyword_id = insert_keyword(keyword)
                    if keyword_id:
                        link_paper_keyword(paper_id, keyword_id)
                
                # Insert statistics
                stats_data = {
                    'word_count': result['stats']['word_count'],
                    'content_length': result['stats']['content_length'],
                    'title_length': result['stats']['title_length'],
                    'num_keywords': result['stats']['num_keywords'],
                    'num_links': result['stats']['num_links']
                }
                insert_stats(paper_id, stats_data)
                
                # Insert discovered links
                for link_data in result['links']:
                    insert_discovered_link(
                        result['url'],
                        link_data['url'],
                        link_data['anchor_text']
                    )
                
                print(f"Worker {self.worker_id}: Successfully stored data for {result['url']}")
            else:
                print(f"Worker {self.worker_id}: Failed to insert paper {result['url']}")
            
        except Exception as e:
            print(f"Worker {self.worker_id}: Error storing data: {e}")
            import traceback
            traceback.print_exc()
    
    def run(self):
        """Main worker loop"""
        self.running = True
        print(f"Worker {self.worker_id}: Started")
        
        self.logger.log_worker_event(self.worker_id, 'START', 'Worker started')
        
        while self.running:
            try:
                # Check if we should continue running
                if not self.redis_client.exists('crawler_running'):
                    print(f"Worker {self.worker_id}: Crawler stopped, exiting...")
                    break
                
                # Get next batch of URLs
                url_batch = self.queue_manager.get_next_batch(self.config.queue.batch_size)
                
                if not url_batch:
                    time.sleep(1)  # No URLs available, wait
                    continue
                
                # Process each URL
                for url_data in url_batch:
                    if not self.running:
                        break
                    
                    url = url_data['url']
                    start_time = time.time()
                    
                    self.logger.log_crawl_start(url, str(self.worker_id))
                    
                    try:
                        # Crawl the page
                        result = self.crawler.crawl_page(url)
                        
                        if result:
                            # Store result in database
                            self._store_crawled_data(result)
                            
                            # Add discovered URLs to queue
                            new_urls = self.queue_manager.add_urls_from_page(result)
                            
                            # Log success
                            duration = time.time() - start_time
                            self.logger.log_crawl_success(url, str(self.worker_id), result['stats'])
                            self.logger.log_performance('crawl_page', duration, {
                                'url': url,
                                'worker_id': self.worker_id,
                                'new_urls_found': new_urls
                            })
                            
                            print(f"Worker {self.worker_id}: Successfully crawled {url}")
                        else:
                            self.logger.log_crawl_error(url, str(self.worker_id), "Failed to crawl page")
                            print(f"Worker {self.worker_id}: Failed to crawl {url}")
                    
                    except Exception as e:
                        self.logger.log_crawl_error(url, str(self.worker_id), str(e))
                        print(f"Worker {self.worker_id}: Error crawling {url}: {e}")
            
            except Exception as e:
                self.logger.log_worker_event(self.worker_id, 'ERROR', f"Worker error: {e}")
                print(f"Worker {self.worker_id}: Error: {e}")
                time.sleep(5)  # Wait before retrying
        
        self.logger.log_worker_event(self.worker_id, 'STOP', 'Worker stopped')
        print(f"Worker {self.worker_id}: Stopped")


def main():
    """Main entry point for standalone worker"""
    parser = argparse.ArgumentParser(description='Standalone worker for distributed crawler')
    parser.add_argument('worker_id', type=int, help='Worker ID')
    parser.add_argument('--config', '-c', help='Configuration file path')
    
    args = parser.parse_args()
    
    # Create and run worker
    worker = StandaloneWorker(args.worker_id, args.config)
    worker.run()


if __name__ == "__main__":
    main()
