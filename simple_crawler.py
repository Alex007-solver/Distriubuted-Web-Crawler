#!/usr/bin/env python3
"""
Simple Crawler - Refactored to use Celery tasks
This serves as an integration test for the new Celery-based architecture.
"""

import sys
import time
import redis
from pathlib import Path
from datetime import datetime

# Add paths
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent / "scripts"))

from scripts.config import ConfigManager
from scripts.logger import init_logger
from scripts.db_sqlalchemy import insert_paper, insert_keyword, link_paper_keyword, insert_stats
from crawler_tasks import crawl_page_task

class SimpleCrawler:
    """Simplified crawler that uses Celery tasks"""
    
    def __init__(self, worker_id):
        self.worker_id = worker_id
        self.running = False
        
        # Load config
        self.config_manager = ConfigManager()
        self.config = self.config_manager.config
        
        # Initialize Redis
        self.redis_client = redis.Redis(
            host=self.config.redis.host,
            port=self.config.redis.port,
            db=self.config.redis.db,
            decode_responses=True
        )
        
        # Initialize logger
        self.logger = init_logger(self.redis_client, self.config.logging.__dict__)
        
        print(f"SimpleCrawler {worker_id}: Initialized (Celery-based)")
    
    def test_crawl_url(self, url):
        """Test crawling a single URL via Celery task"""
        print(f"Worker {self.worker_id}: Testing crawl of {url}")
        
        try:
            # Submit crawl task to Celery
            task_result = crawl_page_task.delay(url, str(self.worker_id))
            
            print(f"Worker {self.worker_id}: Submitted task {task_result.id}")
            
            # Wait for result (with timeout)
            timeout = 60  # 60 seconds timeout
            start_time = time.time()
            
            while not task_result.ready():
                if time.time() - start_time > timeout:
                    print(f"Worker {self.worker_id}: Task timeout for {url}")
                    return None
                time.sleep(1)
            
            if task_result.successful():
                result = task_result.get()
                print(f"Worker {self.worker_id}: Successfully crawled {url}")
                return result
            else:
                error = task_result.result
                print(f"Worker {self.worker_id}: Task failed for {url}: {error}")
                return None
                
        except Exception as e:
            print(f"Worker {self.worker_id}: Error submitting task for {url}: {e}")
            return None
    
    def verify_database_insertion(self, url):
        """Verify that data was inserted into database"""
        try:
            from models import get_db_session, Paper
            
            session = get_db_session()
            paper = session.query(Paper).filter_by(url=url).first()
            session.close()
            
            if paper:
                print(f"Worker {self.worker_id}: ✅ Verified paper in database: {paper.title}")
                return True
            else:
                print(f"Worker {self.worker_id}: ❌ Paper not found in database: {url}")
                return False
                
        except Exception as e:
            print(f"Worker {self.worker_id}: Error verifying database: {e}")
            return False
    
    def run_test(self, test_urls):
        """Run integration test with provided URLs"""
        print(f"Worker {self.worker_id}: Starting integration test...")
        
        success_count = 0
        total_count = len(test_urls)
        
        for url in test_urls:
            print(f"\nWorker {self.worker_id}: Testing URL {url}")
            
            # Test crawling via Celery
            result = self.test_crawl_url(url)
            
            if result:
                success_count += 1
                # Verify database insertion
                self.verify_database_insertion(url)
            else:
                print(f"Worker {self.worker_id}: ❌ Failed to crawl {url}")
            
            time.sleep(2)  # Small delay between requests
        
        print(f"\nWorker {self.worker_id}: Test completed: {success_count}/{total_count} URLs successful")
        return success_count


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Simple Crawler (Celery Integration Test)')
    parser.add_argument('worker_id', type=int, help='Worker ID')
    parser.add_argument('--urls', nargs='+', help='Test URLs (default: built-in test URLs)')
    args = parser.parse_args()
    
    # Default test URLs
    test_urls = args.urls or [
        'https://httpbin.org/html',
        'https://example.com',
        'https://arxiv.org/'
    ]
    
    print(f"Starting SimpleCrawler {args.worker_id} with {len(test_urls)} test URLs")
    print("Make sure Celery workers are running: celery -A celery_app worker --loglevel=info")
    
    # Create and run crawler
    crawler = SimpleCrawler(args.worker_id)
    success_count = crawler.run_test(test_urls)
    
    print(f"\nFinal result: {success_count}/{len(test_urls)} URLs processed successfully")
    
    if success_count == len(test_urls):
        print("✅ All tests passed! Celery integration is working.")
    else:
        print("❌ Some tests failed. Check Celery worker logs.")


if __name__ == "__main__":
    main()
