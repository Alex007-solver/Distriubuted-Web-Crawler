"""
Celery tasks for distributed web crawler
Moves crawling orchestration from manual Redis loops to proper Celery tasks
"""

import sys
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add scripts directory to path
sys.path.append(str(Path(__file__).parent / "scripts"))

from celery_app import app
from config import ConfigManager
from logger import init_logger, get_logger
from general_crawler import GeneralWebCrawler
from db_sqlalchemy import (
    insert_paper, insert_keyword, link_paper_keyword, insert_stats, insert_discovered_link,
    insert_arxiv_paper, insert_arxiv_author, link_arxiv_paper_author,
    insert_arxiv_subject, link_arxiv_paper_subject, insert_arxiv_keyword, 
    link_arxiv_paper_keyword, insert_arxiv_stats
)
from utils import parse_abstract
from robots import check_robots_and_wait
import redis

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global Redis client for rate limiting
redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True
)

@app.task(
    bind=True, 
    name='crawler_tasks.crawl_page', 
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True
)
def crawl_page_task(self, url: str, worker_id: Optional[str] = None):
    """
    Celery task to crawl a single web page
    Replaces manual crawling logic from worker.py
    """
    task_id = self.request.id
    worker_id = worker_id or f"celery-{task_id[:8]}"
    
    try:
        # Initialize components
        config_manager = ConfigManager()
        config = config_manager.config
        crawler_logger = init_logger(redis_client, config.logging.__dict__)
        crawler = GeneralWebCrawler(redis_client, config.crawler.__dict__)
        
        crawler_logger.log_crawl_start(url, worker_id)
        
        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Starting crawl', 'url': url, 'worker_id': worker_id}
        )
        
        # Check robots.txt and rate limiting
        if not check_robots_and_wait(url, redis_client):
            crawler_logger.log_crawl_error(url, worker_id, "Blocked by robots.txt")
            return {'status': 'failed', 'error': 'Blocked by robots.txt', 'url': url}
        
        # Crawl page
        start_time = time.time()
        result = crawler.crawl_page(url)
        
        if not result:
            crawler_logger.log_crawl_error(url, worker_id, "Failed to crawl page")
            return {'status': 'failed', 'error': 'Failed to crawl page', 'url': url}
        
        # Store crawled data
        paper_id = store_crawled_data(result, worker_id)
        
        # Add discovered URLs to queue
        new_urls = len(result.get('links', []))
        
        # Log success
        duration = time.time() - start_time
        crawler_logger.log_crawl_success(url, worker_id, result['stats'])
        crawler_logger.log_performance('crawl_page', duration, {
            'url': url,
            'worker_id': worker_id,
            'new_urls_found': new_urls
        })
        
        # Update task state
        self.update_state(
            state='SUCCESS',
            meta={
                'status': 'completed',
                'url': url,
                'paper_id': paper_id,
                'new_urls_found': new_urls,
                'duration': duration
            }
        )
        
        return {
            'status': 'completed',
            'url': url,
            'paper_id': paper_id,
            'new_urls_found': new_urls,
            'duration': duration,
            'worker_id': worker_id
        }
        
    except Exception as exc:
        logger.error(f"Error crawling {url}: {exc}")
        
        # Log final failure if max retries reached
        crawler_logger = init_logger(redis_client)
        crawler_logger.log_crawl_error(url, worker_id, str(exc))
        
        return {
            'status': 'failed',
            'error': str(exc),
            'url': url,
            'retries': self.request.retries
        }

@app.task(
    bind=True, 
    name='crawler_tasks.process_arxiv_paper', 
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True
)
def process_arxiv_paper_task(self, url: str, worker_id: Optional[str] = None):
    """
    Celery task to process ArXiv paper
    Uses specialized ArXiv scraper with centralized rate limiting
    """
    task_id = self.request.id
    worker_id = worker_id or f"celery-{task_id[:8]}"
    
    try:
        # Extract paper ID from URL
        paper_id = extract_arxiv_id(url)
        if not paper_id:
            return {'status': 'failed', 'error': 'Could not extract ArXiv paper ID', 'url': url}
        
        # Initialize logger
        crawler_logger = init_logger(redis_client)
        crawler_logger.log_crawl_start(url, worker_id)
        
        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Starting ArXiv processing', 'url': url, 'worker_id': worker_id}
        )
        
        # Check robots.txt and rate limiting
        if not check_robots_and_wait(url, redis_client):
            crawler_logger.log_crawl_error(url, worker_id, "Blocked by robots.txt")
            return {'status': 'failed', 'error': 'Blocked by robots.txt', 'url': url}
        
        # Parse ArXiv paper
        start_time = time.time()
        paper_data = parse_abstract(paper_id, redis_client)
        
        if not paper_data:
            crawler_logger.log_crawl_error(url, worker_id, "Failed to parse ArXiv paper")
            return {'status': 'failed', 'error': 'Failed to parse ArXiv paper', 'url': url}
        
        # Store ArXiv data
        paper_id_db = store_arxiv_data(paper_data, worker_id)
        
        if paper_id_db:
            # Log success
            duration = time.time() - start_time
            crawler_logger.log_crawl_success(url, worker_id, {'word_count': paper_data.get('word_count', 0)})
            crawler_logger.log_performance('process_arxiv_paper', duration, {
                'url': url,
                'worker_id': worker_id,
                'paper_id': paper_id_db
            })
            
            # Update task state
            self.update_state(
                state='SUCCESS',
                meta={
                    'status': 'completed',
                    'url': url,
                    'paper_id': paper_id_db,
                    'duration': duration
                }
            )
            
            return {
                'status': 'completed',
                'url': url,
                'paper_id': paper_id_db,
                'duration': duration,
                'worker_id': worker_id
            }
        else:
            crawler_logger.log_crawl_error(url, worker_id, "Failed to store ArXiv data")
            return {'status': 'failed', 'error': 'Failed to store ArXiv data', 'url': url}
            
    except Exception as exc:
        logger.error(f"Error processing ArXiv paper {url}: {exc}")
        
        # Log final failure if max retries reached
        crawler_logger = init_logger(redis_client)
        crawler_logger.log_crawl_error(url, worker_id, str(exc))
        
        return {
            'status': 'failed',
            'error': str(exc),
            'url': url,
            'retries': self.request.retries
        }

@app.task(
    bind=True, 
    name='crawler_tasks.batch_crawl', 
    max_retries=1,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=30,
    retry_jitter=True
)
def batch_crawl_task(self, urls: list, worker_id: Optional[str] = None):
    """
    Celery task to crawl multiple URLs in batch
    """
    task_id = self.request.id
    worker_id = worker_id or f"celery-{task_id[:8]}"
    
    try:
        results = []
        
        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Starting batch crawl', 'total_urls': len(urls), 'worker_id': worker_id}
        )
        
        for i, url in enumerate(urls):
            # Route URL based on type
            if is_arxiv_url(url):
                result = process_arxiv_paper_task.apply_async(args=[url, worker_id])
            else:
                result = crawl_page_task.apply_async(args=[url, worker_id])
            
            results.append({
                'url': url,
                'task_id': result.id,
                'index': i
            })
        
        # Update task state
        self.update_state(
            state='SUCCESS',
            meta={
                'status': 'batch submitted',
                'total_urls': len(urls),
                'results': results,
                'worker_id': worker_id
            }
        )
        
        return {
            'status': 'batch_submitted',
            'total_urls': len(urls),
            'results': results,
            'worker_id': worker_id
        }
        
    except Exception as exc:
        logger.error(f"Error in batch crawl: {exc}")
        
        return {
            'status': 'failed',
            'error': str(exc),
            'retries': self.request.retries
        }

# Helper functions
def is_arxiv_url(url: str) -> bool:
    """Check if URL is an ArXiv URL"""
    return 'arxiv.org' in url.lower()

def extract_arxiv_id(url: str) -> Optional[str]:
    """Extract ArXiv paper ID from URL"""
    import re
    # Match patterns like /abs/2301.12345 or /pdf/2301.12345.pdf
    match = re.search(r'/abs/(\d+\.\d+)', url)
    if match:
        return match.group(1)
    return None

def store_crawled_data(result: Dict[str, Any], worker_id: str) -> Optional[int]:
    """Store crawled data using SQLAlchemy with resilient transactions"""
    session = None
    try:
        # Get database session
        from models import get_db_session
        session = get_db_session()
        
        # Prepare paper data
        paper_data = {
            'url': result['url'],
            'title': result['title'],
            'content': result['content'],
            'content_hash': result['content_hash'],
            'domain': result['metadata']['domain'],
            'status': 'COMPLETED',  # Fix: Use uppercase enum value
            'priority': 50,
            'crawl_date': datetime.fromtimestamp(result['crawl_date'])
        }
        
        # Insert main paper (this must succeed)
        paper_id = insert_paper(paper_data)
        
        if paper_id:
            # Insert keywords and link them (resilient - failures won't roll back main paper)
            for keyword in result['keywords']:
                try:
                    keyword_id = insert_keyword(keyword)
                    if keyword_id:
                        link_paper_keyword(paper_id, keyword_id)
                except Exception as e:
                    logger.warning(f"Worker {worker_id}: Failed to insert keyword '{keyword}': {e}")
            
            # Insert statistics (resilient)
            try:
                stats_data = {
                    'word_count': result['stats']['word_count'],
                    'content_length': result['stats']['content_length'],
                    'title_length': result['stats']['title_length'],
                    'num_keywords': result['stats']['num_keywords'],
                    'num_links': result['stats']['num_links']
                }
                insert_stats(paper_id, stats_data)
            except Exception as e:
                logger.warning(f"Worker {worker_id}: Failed to insert stats: {e}")
            
            # Insert discovered links (resilient)
            for link_data in result.get('links', []):
                try:
                    insert_discovered_link(
                        result['url'],
                        link_data['url'],
                        link_data['anchor_text']
                    )
                except Exception as e:
                    logger.warning(f"Worker {worker_id}: Failed to insert discovered link: {e}")
            
            logger.info(f"Worker {worker_id}: Successfully stored data for {result['url']}")
            return paper_id
        else:
            logger.error(f"Worker {worker_id}: Failed to insert paper {result['url']}")
            return None
            
    except Exception as e:
        logger.error(f"Worker {worker_id}: Database error storing data for {result.get('url', 'unknown')}: {e}")
        return None
    finally:
        if session:
            session.close()

def store_arxiv_data(paper_data: Dict, worker_id: str) -> Optional[int]:
    """Store ArXiv paper data using SQLAlchemy with resilient transactions"""
    session = None
    try:
        # Get database session
        from models import get_arxiv_db_session
        session = get_arxiv_db_session()
        
        # Insert main paper (this must succeed)
        paper_id = insert_arxiv_paper(paper_data)
        
        if paper_id:
            # Insert and link authors (resilient)
            for author in paper_data.get('authors', []):
                try:
                    author_id = insert_arxiv_author(author)
                    if author_id:
                        link_arxiv_paper_author(paper_id, author_id)
                except Exception as e:
                    logger.warning(f"Worker {worker_id}: Failed to insert author '{author}': {e}")
            
            # Insert and link subjects (resilient)
            for subject in paper_data.get('subjects', []):
                try:
                    subject_id = insert_arxiv_subject(subject)
                    if subject_id:
                        link_arxiv_paper_subject(paper_id, subject_id)
                except Exception as e:
                    logger.warning(f"Worker {worker_id}: Failed to insert subject '{subject}': {e}")
            
            # Insert and link keywords (resilient)
            for keyword in paper_data.get('keywords', []):
                try:
                    keyword_id = insert_arxiv_keyword(keyword)
                    if keyword_id:
                        link_arxiv_paper_keyword(paper_id, keyword_id)
                except Exception as e:
                    logger.warning(f"Worker {worker_id}: Failed to insert keyword '{keyword}': {e}")
            
            # Insert statistics (resilient)
            try:
                stats_data = {
                    'word_count': paper_data.get('word_count', 0),
                    'abstract_length': paper_data.get('abstract_length', 0),
                    'title_length': paper_data.get('title_length', 0),
                    'num_authors': paper_data.get('num_authors', 0),
                    'num_keywords': paper_data.get('num_keywords', 0)
                }
                insert_arxiv_stats(paper_id, stats_data)
            except Exception as e:
                logger.warning(f"Worker {worker_id}: Failed to insert ArXiv stats: {e}")
                
            logger.info(f"Worker {worker_id}: Successfully stored ArXiv data for paper {paper_id}")
            return paper_id
        else:
            logger.error(f"Worker {worker_id}: Failed to insert ArXiv paper")
            return None
            
    except Exception as e:
        logger.error(f"Worker {worker_id}: Database error storing ArXiv data: {e}")
        return None
    finally:
        if session:
            session.close()
