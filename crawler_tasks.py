"""
Celery tasks for distributed web crawler
Refactors crawl_page function and other operations into Celery tasks
"""

import sys
import time
import logging
from pathlib import Path
from celery import current_task
from celery.exceptions import Retry

# Add scripts directory to path
sys.path.append(str(Path(__file__).parent / "scripts"))

from celery_app import app
from general_crawler import GeneralWebCrawler
from db_sqlalchemy import (
    insert_paper, insert_keyword, link_paper_keyword,
    insert_stats, insert_discovered_link,
    insert_arxiv_paper, insert_arxiv_author, link_arxiv_paper_author,
    insert_arxiv_subject, link_arxiv_paper_subject,
    insert_arxiv_keyword, link_arxiv_paper_keyword, insert_arxiv_stats
)
from utils import parse_abstract, extract_keywords, compute_stats
from url_queue import QueueManager
from logger import init_logger
from robots import check_robots_and_wait
import redis

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis client for coordination
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

@app.task(bind=True, name='crawler_tasks.crawl_page', max_retries=3)
def crawl_page_task(self, url, worker_id=None):
    """
    Celery task to crawl a single web page
    Replaces the crawl_page function from general_crawler.py
    """
    task_id = self.request.id
    worker_id = worker_id or f"celery-{task_id[:8]}"
    
    try:
        # Initialize components
        crawler_logger = init_logger(redis_client)
        crawler = GeneralWebCrawler(redis_client)
        
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
        
        # Crawl the page
        start_time = time.time()
        result = crawler.crawl_page(url)
        
        if not result:
            crawler_logger.log_crawl_error(url, worker_id, "Failed to crawl page")
            return {'status': 'failed', 'error': 'Failed to crawl page', 'url': url}
        
        # Store crawled data
        paper_id = store_crawled_data(result, worker_id)
        
        # Add discovered URLs to queue
        queue_manager = QueueManager(redis_client)
        new_urls = queue_manager.add_urls_from_page(result)
        
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
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            countdown = 2 ** self.request.retries  # Exponential backoff
            logger.info(f"Retrying crawl of {url} in {countdown} seconds (attempt {self.request.retries + 1})")
            raise self.retry(countdown=countdown, exc=exc)
        
        # Log final failure
        crawler_logger = init_logger(redis_client)
        crawler_logger.log_crawl_error(url, worker_id, str(exc))
        
        return {
            'status': 'failed',
            'error': str(exc),
            'url': url,
            'retries': self.request.retries
        }

@app.task(bind=True, name='crawler_tasks.process_arxiv_paper', max_retries=3)
def process_arxiv_paper_task(self, paper_id, worker_id=None):
    """
    Celery task to process an arXiv paper
    Replaces the arXiv worker functionality
    """
    task_id = self.request.id
    worker_id = worker_id or f"celery-{task_id[:8]}"
    
    try:
        # Initialize logger
        crawler_logger = init_logger(redis_client)
        
        crawler_logger.log_worker_event(worker_id, 'START', f"Processing arXiv paper {paper_id}")
        
        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Parsing paper', 'paper_id': paper_id, 'worker_id': worker_id}
        )
        
        # Parse arXiv paper
        paper_data = parse_abstract(paper_id, redis_client)
        
        if not paper_data:
            crawler_logger.log_crawl_error(f"arxiv:{paper_id}", worker_id, "Failed to parse paper")
            return {'status': 'failed', 'error': 'Failed to parse paper', 'paper_id': paper_id}
        
        # Store paper data
        paper_db_id = store_arxiv_data(paper_data, worker_id)
        
        # Update task state
        self.update_state(
            state='SUCCESS',
            meta={
                'status': 'completed',
                'paper_id': paper_id,
                'paper_db_id': paper_db_id,
                'worker_id': worker_id
            }
        )
        
        crawler_logger.log_worker_event(worker_id, 'COMPLETE', f"Processed arXiv paper {paper_id}")
        
        return {
            'status': 'completed',
            'paper_id': paper_id,
            'paper_db_id': paper_db_id,
            'worker_id': worker_id
        }
        
    except Exception as exc:
        logger.error(f"Error processing arXiv paper {paper_id}: {exc}")
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            countdown = 2 ** self.request.retries
            logger.info(f"Retrying arXiv paper {paper_id} in {countdown} seconds")
            raise self.retry(countdown=countdown, exc=exc)
        
        return {
            'status': 'failed',
            'error': str(exc),
            'paper_id': paper_id,
            'retries': self.request.retries
        }

@app.task(name='crawler_tasks.batch_crawl')
def batch_crawl_task(urls, worker_id=None):
    """
    Celery task to crawl multiple URLs in batch
    """
    results = []
    
    for url in urls:
        try:
            result = crawl_page_task.delay(url, worker_id)
            results.append(result)
        except Exception as e:
            logger.error(f"Error queuing crawl for {url}: {e}")
    
    return {
        'status': 'queued',
        'queued_tasks': len(results),
        'task_ids': [result.id for result in results]
    }

@app.task(name='crawler_tasks.analyze_content')
def analyze_content_task(paper_id, worker_id=None):
    """
    Celery task to analyze crawled content
    """
    try:
        from db_sqlalchemy import get_db_session
        from models import Paper
        
        session = get_db_session()
        paper = session.query(Paper).filter_by(id=paper_id).first()
        
        if not paper:
            return {'status': 'failed', 'error': 'Paper not found', 'paper_id': paper_id}
        
        # Perform content analysis
        analysis = {
            'word_count': len(paper.content.split()) if paper.content else 0,
            'keyword_density': {},
            'readability_score': calculate_readability(paper.content) if paper.content else 0
        }
        
        # Extract keyword density
        if paper.content:
            from collections import Counter
            words = paper.content.lower().split()
            word_freq = Counter(words)
            total_words = len(words)
            
            for word, count in word_freq.most_common(10):
                analysis['keyword_density'][word] = (count / total_words) * 100
        
        session.close()
        
        return {
            'status': 'completed',
            'paper_id': paper_id,
            'analysis': analysis,
            'worker_id': worker_id
        }
        
    except Exception as e:
        logger.error(f"Error analyzing content for paper {paper_id}: {e}")
        return {
            'status': 'failed',
            'error': str(e),
            'paper_id': paper_id
        }

def store_crawled_data(result, worker_id):
    """Store crawled data using SQLAlchemy"""
    try:
        # Prepare paper data
        paper_data = {
            'url': result['url'],
            'title': result['title'],
            'content': result['content'],
            'content_hash': result['content_hash'],
            'domain': result['metadata']['domain'],
            'status': 'completed',
            'priority': 50,
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
            
            logger.info(f"Worker {worker_id}: Successfully stored data for {result['url']}")
            return paper_id
        else:
            logger.error(f"Worker {worker_id}: Failed to insert paper {result['url']}")
            return None
            
    except Exception as e:
        logger.error(f"Worker {worker_id}: Error storing data: {e}")
        return None

def store_arxiv_data(paper_data, worker_id):
    """Store arXiv paper data using SQLAlchemy"""
    try:
        # Insert main paper
        paper_id = insert_arxiv_paper(paper_data)
        
        if paper_id:
            # Insert and link authors
            for author in paper_data.get('authors', []):
                author_id = insert_arxiv_author(author)
                if author_id:
                    link_arxiv_paper_author(paper_id, author_id)
            
            # Insert and link subjects
            for subject in paper_data.get('subjects', []):
                subject_id = insert_arxiv_subject(subject)
                if subject_id:
                    link_arxiv_paper_subject(paper_id, subject_id)
            
            # Extract and link keywords
            keywords = extract_keywords(paper_data.get('abstract', ''))
            for keyword in keywords:
                keyword_id = insert_arxiv_keyword(keyword)
                if keyword_id:
                    link_arxiv_paper_keyword(paper_id, keyword_id)
            
            # Insert statistics
            stats = compute_stats(paper_data)
            insert_arxiv_stats(paper_id, stats)
            
            logger.info(f"Worker {worker_id}: Successfully stored arXiv paper {paper_data['paper_id']}")
            return paper_id
        else:
            logger.error(f"Worker {worker_id}: Failed to insert arXiv paper {paper_data['paper_id']}")
            return None
            
    except Exception as e:
        logger.error(f"Worker {worker_id}: Error storing arXiv data: {e}")
        return None

def calculate_readability(text):
    """Simple readability score calculation"""
    if not text:
        return 0
    
    sentences = text.split('.')
    words = text.split()
    
    if len(sentences) == 0:
        return 0
    
    avg_words_per_sentence = len(words) / len(sentences)
    avg_chars_per_word = sum(len(word) for word in words) / len(words) if words else 0
    
    # Simple readability formula (inverse of words per sentence + chars per word)
    readability = 100 - (1.015 * avg_words_per_sentence) - (84.6 * (avg_chars_per_word / 4.7))
    return max(0, min(100, readability))

# Maintenance tasks
@app.task(name='maintenance_tasks.cleanup_old_logs')
def cleanup_old_logs():
    """Clean up old logs from Redis"""
    try:
        logger = init_logger(redis_client)
        logger.cleanup_old_entries(days=7)
        return {'status': 'completed', 'message': 'Old logs cleaned up'}
    except Exception as e:
        logger.error(f"Error cleaning up logs: {e}")
        return {'status': 'failed', 'error': str(e)}

@app.task(name='maintenance_tasks.update_stats')
def update_stats():
    """Update crawler statistics"""
    try:
        from db_sqlalchemy import update_crawler_stats
        from models import get_db_session, Paper, CrawlerStats
        
        session = get_db_session()
        
        # Count papers
        total_papers = session.query(Paper).count()
        completed_papers = session.query(Paper).filter_by(status='completed').count()
        
        # Update stats
        stats_data = {
            'total_pages_crawled': completed_papers,
            'total_urls_discovered': total_papers,
            'active_workers': len(redis_client.smembers('active_workers')),
            'error_count': redis_client.get('error_count') or 0
        }
        
        update_crawler_stats(stats_data)
        session.close()
        
        return {'status': 'completed', 'stats': stats_data}
    except Exception as e:
        logger.error(f"Error updating stats: {e}")
        return {'status': 'failed', 'error': str(e)}
