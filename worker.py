#!/usr/bin/env python3
"""
Distributed Web Crawler Worker
Simplified worker that just starts Celery worker process
"""

import sys
import signal
import logging
from pathlib import Path
import time

# Add scripts directory to path
sys.path.append(str(Path(__file__).parent / "scripts"))

import subprocess
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CeleryWorkerLauncher:
    """Simple launcher for Celery workers"""
    
    def __init__(self, queues=None, worker_id=None):
        self.queues = queues or ['crawling', 'arxiv']
        self.worker_id = worker_id or f"worker-{int(time.time())}"
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\nWorker {self.worker_id}: Received signal {signum}, shutting down...")
        sys.exit(0)
    
    def start_celery_worker(self):
        """Start Celery worker process"""
        try:
            print(f"Starting Celery worker {self.worker_id} with queues: {self.queues}")
            
            # Build celery command
            cmd = [
                sys.executable, '-m', 'celery', 
                '-A', 'celery_app',
                'worker',
                '--loglevel=info',
                f'--queues={",".join(self.queues)}',
                f'--hostname={self.worker_id}',
                '--concurrency=4',
                '--prefetch-multiplier=1',
                '--max-tasks-per-child=1000'
            ]
            
            # Start celery worker
            process = subprocess.Popen(cmd, cwd=Path(__file__).parent)
            
            # Wait for process to complete
            process.wait()
            
        except KeyboardInterrupt:
            print(f"\nWorker {self.worker_id}: Interrupted by user")
        except Exception as e:
            logger.error(f"Error starting Celery worker: {e}")
            print(f"Error starting Celery worker: {e}")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Distributed Web Crawler Celery Worker')
    parser.add_argument('--worker-id', help='Custom worker ID')
    parser.add_argument('--queues', help='Comma-separated list of queues (default: crawling,arxiv)')
    parser.add_argument('--concurrency', type=int, default=4, help='Number of concurrent processes')
    parser.add_argument('--daemon', action='store_true', help='Run in daemon mode')
    
    args = parser.parse_args()
    
    # Parse queues
    queues = None
    if args.queues:
        queues = [q.strip() for q in args.queues.split(',')]
    
    # Create and start worker launcher
    launcher = CeleryWorkerLauncher(queues, args.worker_id)
    launcher.start_celery_worker()

if __name__ == "__main__":
    main()
