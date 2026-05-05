"""
Celery configuration for distributed web crawler
Replaces custom Redis queue with Celery task distribution
"""

from celery import Celery
from kombu import Queue
import os

# Celery configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'rpc://')

# Create Celery app with auto-discovery
app = Celery('distributed_crawler', include=['crawler_tasks'])

# Configure Celery
app.conf.update(
    broker_url=CELERY_BROKER_URL,
    result_backend=CELERY_RESULT_BACKEND,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task routing
    task_routes={
        'crawler_tasks.crawl_page': {'queue': 'crawling'},
        'crawler_tasks.process_arxiv_paper': {'queue': 'arxiv'},
        'crawler_tasks.batch_crawl': {'queue': 'crawling'},
        'crawler_tasks.analyze_content': {'queue': 'analysis'}
    },
    
    # Queue definitions
    task_queues=(
        Queue('crawling', routing_key='crawling'),
        Queue('arxiv', routing_key='arxiv'),
        Queue('analysis', routing_key='analysis'),
        Queue('default', routing_key='default'),
    ),
    
    # Worker configuration
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    
    # Task timeouts
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,       # 10 minutes
    
    # Result expiration
    result_expires=3600,  # 1 hour
    
    # Error handling
    task_reject_on_worker_lost=True,
    task_ignore_result=False,
)

# Optional: Configure beat scheduler for periodic tasks
app.conf.beat_schedule = {
    'cleanup-old-logs': {
        'task': 'maintenance_tasks.cleanup_old_logs',
        'schedule': 3600.0,  # Every hour
    },
    'update-crawler-stats': {
        'task': 'maintenance_tasks.update_stats',
        'schedule': 300.0,  # Every 5 minutes
    },
}

if __name__ == '__main__':
    app.start()
