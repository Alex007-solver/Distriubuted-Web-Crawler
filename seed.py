#!/usr/bin/env python3
"""
Distributed Web Crawler Seed Script
Initialize Redis queue with starter URLs for crawling
"""

import sys
import redis
from pathlib import Path
from typing import List, Dict, Any

# Add scripts directory to path
sys.path.append(str(Path(__file__).parent / "scripts"))

from config import ConfigManager

class QueueSeeder:
    """Utility to seed the Redis queue with starter URLs"""
    
    def __init__(self):
        # Load configuration
        self.config_manager = ConfigManager()
        self.config = self.config_manager.config
        
        # Initialize Redis client
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
        except redis.ConnectionError as e:
            print(f"✗ Failed to connect to Redis: {e}")
            sys.exit(1)
        
        print("✓ Queue seeder initialized")
    
    def clear_queue(self, queue_name: str) -> int:
        """Clear a specific queue"""
        try:
            length = self.redis_client.llen(queue_name)
            self.redis_client.delete(queue_name)
            print(f"✓ Cleared {queue_name} (removed {length} URLs)")
            return length
        except redis.RedisError as e:
            print(f"✗ Error clearing {queue_name}: {e}")
            return 0
    
    def clear_all_queues(self) -> Dict[str, int]:
        """Clear all URL queues"""
        queues = ["url_queue:high", "url_queue:default", "url_queue:low"]
        results = {}
        
        for queue in queues:
            results[queue] = self.clear_queue(queue)
        
        total_cleared = sum(results.values())
        print(f"✓ Cleared all queues (removed {total_cleared} total URLs)")
        return results
    
    def add_url(self, url: str, priority: str = "default") -> bool:
        """Add a single URL to the specified queue"""
        queue_name = f"url_queue:{priority}"
        
        if queue_name not in ["url_queue:high", "url_queue:default", "url_queue:low"]:
            print(f"✗ Invalid priority: {priority}. Use 'high', 'default', or 'low'")
            return False
        
        try:
            self.redis_client.rpush(queue_name, url)
            print(f"✓ Added {url} to {queue_name}")
            return True
        except redis.RedisError as e:
            print(f"✗ Error adding URL to queue: {e}")
            return False
    
    def add_urls(self, urls: List[str], priority: str = "default") -> int:
        """Add multiple URLs to the specified queue"""
        queue_name = f"url_queue:{priority}"
        
        if queue_name not in ["url_queue:high", "url_queue:default", "url_queue:low"]:
            print(f"✗ Invalid priority: {priority}. Use 'high', 'default', or 'low'")
            return 0
        
        try:
            # Add URLs in batch
            pipe = self.redis_client.pipeline()
            for url in urls:
                pipe.rpush(queue_name, url)
            pipe.execute()
            
            print(f"✓ Added {len(urls)} URLs to {queue_name}")
            return len(urls)
        except redis.RedisError as e:
            print(f"✗ Error adding URLs to queue: {e}")
            return 0
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current status of all queues"""
        queues = ["url_queue:high", "url_queue:default", "url_queue:low"]
        status = {}
        
        for queue in queues:
            try:
                length = self.redis_client.llen(queue)
                status[queue] = {
                    'length': length,
                    'status': 'active' if length > 0 else 'empty'
                }
            except redis.RedisError as e:
                status[queue] = {
                    'length': 0,
                    'status': f'error: {e}'
                }
        
        return status
    
    def print_status(self):
        """Print current queue status"""
        status = self.get_queue_status()
        
        print("\n" + "="*50)
        print("QUEUE STATUS")
        print("="*50)
        
        for queue, info in status.items():
            print(f"{queue}:")
            print(f"  Length: {info['length']}")
            print(f"  Status: {info['status']}")
        
        print("="*50)
    
    def seed_default_urls(self) -> int:
        """Seed the queue with default starter URLs"""
        default_urls = {
            "high": [
                "https://arxiv.org/list/cs.AI/recent",
                "https://arxiv.org/list/cs.LG/recent",
                "https://en.wikipedia.org/wiki/Web_crawler",
                "https://en.wikipedia.org/wiki/Distributed_computing",
                "https://github.com/topics/web-crawler"
            ],
            "default": [
                "https://httpbin.org/html",
                "https://example.com",
                "https://httpbin.org/links/5",
                "https://jsonplaceholder.typicode.com/posts/1",
                "https://reqres.in/api/users/1"
            ],
            "low": [
                "https://www.w3.org/Protocols/rfc2616/rfc2616.html",
                "https://tools.ietf.org/html/rfc3986",
                "https://www.iana.org/domains/root/db"
            ]
        }
        
        total_added = 0
        
        print("Seeding queues with default URLs...")
        
        for priority, urls in default_urls.items():
            added = self.add_urls(urls, priority)
            total_added += added
        
        print(f"✓ Seeded queues with {total_added} default URLs")
        return total_added
    
    def seed_from_file(self, file_path: str, priority: str = "default") -> int:
        """Seed URLs from a file (one URL per line)"""
        try:
            with open(file_path, 'r') as f:
                urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            return self.add_urls(urls, priority)
            
        except FileNotFoundError:
            print(f"✗ File not found: {file_path}")
            return 0
        except Exception as e:
            print(f"✗ Error reading file: {e}")
            return 0

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Distributed Web Crawler Queue Seeder')
    parser.add_argument('--config', '-c', help='Configuration file path')
    parser.add_argument('--clear', action='store_true', help='Clear all queues before seeding')
    parser.add_argument('--status', action='store_true', help='Show current queue status')
    parser.add_argument('--default', action='store_true', help='Seed with default URLs')
    parser.add_argument('--file', help='Seed URLs from file (one per line)')
    parser.add_argument('--url', help='Add a single URL')
    parser.add_argument('--priority', choices=['high', 'default', 'low'], default='default', help='Queue priority')
    parser.add_argument('--urls', nargs='+', help='Add multiple URLs')
    
    args = parser.parse_args()
    
    # Create seeder
    seeder = QueueSeeder()
    
    # Show status if requested
    if args.status:
        seeder.print_status()
        return
    
    # Clear queues if requested
    if args.clear:
        seeder.clear_all_queues()
    
    # Add URLs based on arguments
    if args.default:
        seeder.seed_default_urls()
    elif args.file:
        seeder.seed_from_file(args.file, args.priority)
    elif args.url:
        seeder.add_url(args.url, args.priority)
    elif args.urls:
        seeder.add_urls(args.urls, args.priority)
    else:
        # Default behavior: show status and seed with default URLs
        print("No arguments provided. Showing current status and seeding with default URLs...")
        seeder.print_status()
        seeder.seed_default_urls()
    
    # Show final status
    print("\nFinal queue status:")
    seeder.print_status()

if __name__ == "__main__":
    main()
