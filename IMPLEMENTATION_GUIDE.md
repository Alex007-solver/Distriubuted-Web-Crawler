# Implementation Guide: Distributed Web Crawler Updates

This document explains how each of the 5 major updates integrates with the existing distributed web crawler system.

## Overview

The distributed web crawler has been enhanced with 5 significant updates that fulfill specific assignment requirements while maintaining backward compatibility with the existing arXiv crawler functionality.

---

## Update 1: Refactor Database Operations to use SQLAlchemy

### What Was Added
- **`models.py`**: Complete SQLAlchemy ORM models for both general crawler and arXiv databases
- **`scripts/db_sqlalchemy.py`**: New database operations using SQLAlchemy sessions
- **Updated `standalone_worker.py`**: Modified to use SQLAlchemy instead of raw SQL

### Integration with Existing System

#### Backward Compatibility
```python
# Legacy functions still work
from scripts.db_sqlalchemy import get_connection, insert_paper_legacy
# These map to the new SQLAlchemy functions internally
```

#### New SQLAlchemy Usage
```python
# New preferred approach
from scripts.db_sqlalchemy import insert_paper, get_db_session
from models import Paper, PaperStats

# Session-based operations
session = get_db_session()
paper = Paper(url="https://example.com", title="Example")
session.add(paper)
session.commit()
```

#### Database Schema Support
- **General Crawler Database (`crawler_db`)**: Full ORM models for papers, authors, keywords, stats, links
- **ArXiv Database (`arxiv_db`)**: Separate ORM models maintaining legacy compatibility
- **Automatic Table Creation**: `DatabaseManager.create_tables()` creates all required tables

#### Migration Path
```bash
# Create new database structure
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS crawler_db;"
mysql -u root -p crawler_db < schema.sql

# Python - create SQLAlchemy tables
python -c "from models import db_manager; db_manager.create_tables()"
```

---

## Update 2: Data Analysis & Visualization (Pandas & Matplotlib/NetworkX)

### What Was Added
- **`analyze_crawler_data.py`**: Comprehensive data analysis script
- **Multiple Visualizations**: Domain analysis, content scatter plots, keyword analysis, network graphs, timeline analysis

### Integration with Existing System

#### Database Integration
```python
# Uses SQLAlchemy models directly
from models import get_db_session, Paper, PaperStats, DiscoveredLink

# Pandas integration for analysis
papers_df = pd.read_sql(query, self.engine)
```

#### Generated Visualizations
1. **Domain Analysis**: Bar chart of most crawled domains
2. **Content Scatter Plot**: Word count vs number of links with keyword density coloring
3. **Keyword Analysis**: Horizontal bar chart of most common keywords
4. **Network Graph**: Interactive visualization of discovered links using NetworkX
5. **Timeline Analysis**: Daily and hourly crawling activity patterns

#### Usage Examples
```bash
# Run complete analysis
python analyze_crawler_data.py --db-url mysql+pymysql://user:pass@localhost/crawler_db

# Custom output directory
python analyze_crawler_data.py --output-dir ./analysis_output
```

#### Integration Points
- **Logger Integration**: Uses existing crawler data structure
- **Redis Integration**: Can analyze Redis queue data if needed
- **Config Integration**: Uses existing configuration patterns

---

## Update 3: Network Packet Analysis (Scapy)

### What Was Added
- **`network_monitor.py`**: Comprehensive network packet monitoring
- **Real-time Analysis**: HTTP/HTTPS/DNS traffic capture and analysis
- **Statistical Reporting**: Target IPs, domains, payload analysis, protocol breakdown

### Integration with Existing System

#### Crawler Traffic Monitoring
```python
# Filters for crawler-specific traffic
filter_expr = "(tcp port 80 or tcp port 443 or udp port 53)"

# Identifies crawler requests by User-Agent
if HTTPRequest in packet and b'DistributedCrawler' in packet[HTTPRequest].User_Agent:
    # This is crawler traffic
```

#### Integration with Redis
```python
# Can correlate network activity with Redis logs
redis_client = redis.Redis(host='localhost', port=6379, db=0)
# Store network stats alongside crawler stats
```

#### Usage Examples
```bash
# Monitor crawler traffic for 2 minutes
sudo python network_monitor.py -d 120 -o network_analysis.json

# List available interfaces
python network_monitor.py --list-interfaces

# Monitor specific interface
sudo python network_monitor.py -i en0 -d 60
```

#### Integration Points
- **Crawler User-Agent**: Identifies crawler requests automatically
- **DNS Analysis**: Tracks domain resolution for crawled sites
- **Performance Monitoring**: Correlates network latency with crawl performance

---

## Update 4: Task Distribution (Celery)

### What Was Added
- **`celery_app.py`**: Celery configuration with Redis broker
- **`crawler_tasks.py`**: All crawler operations converted to Celery tasks
- **Task Routing**: Separate queues for different types of operations

### Integration with Existing System

#### Replacing Custom Worker System
```python
# Old approach (standalone_worker.py)
while True:
    url = queue.get_url()
    result = crawler.crawl_page(url)
    store_data(result)

# New Celery approach
from crawler_tasks import crawl_page_task
result = crawl_page_task.delay(url, worker_id="celery-worker-1")
```

#### Celery Worker Commands
```bash
# Start Celery worker for crawling
celery -A celery_app worker --loglevel=info --queues=crawling

# Start Celery worker for arXiv processing
celery -A celery_app worker --loglevel=info --queues=arxiv

# Start Celery beat scheduler for periodic tasks
celery -A celery_app beat --loglevel=info
```

#### Task Types and Routing
```python
# Main crawling tasks
crawler_tasks.crawl_page -> 'crawling' queue
crawler_tasks.batch_crawl -> 'crawling' queue

# arXiv-specific tasks
crawler_tasks.process_arxiv_paper -> 'arxiv' queue

# Analysis tasks
crawler_tasks.analyze_content -> 'analysis' queue

# Maintenance tasks
maintenance_tasks.cleanup_old_logs -> 'default' queue
maintenance_tasks.update_stats -> 'default' queue
```

#### Integration with Existing Components
- **Redis Integration**: Uses same Redis instance as broker and result backend
- **Database Integration**: Uses new SQLAlchemy models for data storage
- **Logger Integration**: Maintains existing logging patterns
- **Queue Integration**: Replaces custom URL queue with Celery task queue

#### Migration Strategy
```python
# Gradual migration - both systems can coexist
# Use Celery for new crawling, keep arXiv worker for compatibility

# Main orchestrator can dispatch to either system
if url.startswith('https://arxiv.org/'):
    # Use arXiv Celery task
    process_arxiv_paper_task.delay(paper_id)
else:
    # Use general Celery task
    crawl_page_task.delay(url)
```

---

## Update 5: Shell Tools (wget/curl, awk/sed, jq)

### What Was Added
- **`crawler_utils.sh`**: Comprehensive shell utility script
- **Network Testing**: curl/wget for endpoint testing and robots.txt fetching
- **Log Processing**: awk/sed for log analysis and timestamp processing
- **JSON Processing**: jq for extracting data from structured logs

### Integration with Existing System

#### Network Testing Integration
```bash
# Test crawler access to specific sites
./crawler_utils.sh test_crawler_access https://arxiv.org

# Verify robots.txt compliance
./crawler_utils.sh fetch_robots_txt wikipedia.org

# Test endpoint availability
./crawler_utils.sh test_endpoint https://httpbin.org/status/200
```

#### Log Processing Integration
```bash
# Analyze crawler logs
./crawler_utils.sh count_successful_crawls crawler.log

# Extract timestamps in different formats
./crawler_utils.sh extract_timestamps crawler.log iso

# Filter logs by error level
./crawler_utils.sh filter_log_by_level crawler.log ERROR
```

#### JSON Processing Integration
```bash
# Extract crawl errors from JSON logs
./crawler_utils.sh extract_crawl_errors logs.json

# Analyze worker statistics
./crawler_utils.sh extract_worker_stats logs.json

# Filter logs by time range
./crawler_utils.sh filter_json_by_time logs.json last_hour
```

#### Redis Integration
```bash
# Check Redis status
./crawler_utils.sh check_redis_status

# Clear specific data patterns
./crawler_utils.sh clear_redis_data "*crawler*"
```

#### Integration Points
- **Logger Integration**: Processes JSON logs from the existing logger system
- **Redis Integration**: Manages Redis data and checks system status
- **Configuration Integration**: Uses same connection parameters as main system

---

## System Integration Summary

### Backward Compatibility
- **arXiv Crawler**: Continues to work with existing scripts
- **Database Operations**: Legacy functions map to new SQLAlchemy implementations
- **Redis Integration**: All components use same Redis instance
- **Configuration**: Shared configuration patterns maintained

### New Capabilities
- **SQLAlchemy ORM**: Type-safe database operations with automatic migrations
- **Data Visualization**: Rich analysis and reporting capabilities
- **Network Monitoring**: Real-time packet analysis for crawler traffic
- **Distributed Tasks**: Scalable Celery-based task distribution
- **Shell Utilities**: Comprehensive testing and analysis tools

### Migration Path
```bash
# 1. Install new dependencies
pip install sqlalchemy pymysql scapy celery pandas matplotlib networkx

# 2. Set up databases
mysql -u root -p < schema.sql
python -c "from models import db_manager; db_manager.create_tables()"

# 3. Start new services
redis-server
celery -A celery_app worker --loglevel=info

# 4. Run enhanced crawler
python main.py --use-celery

# 5. Analyze results
python analyze_crawler_data.py
sudo python network_monitor.py -d 60
./crawler_utils.sh demo_all
```

### Usage Examples

#### Enhanced Crawling with Celery
```python
# Queue multiple URLs for crawling
from crawler_tasks import batch_crawl_task
result = batch_crawl_task.delay([
    "https://example.com",
    "https://test.com",
    "https://demo.com"
])
```

#### Real-time Network Monitoring
```bash
# Monitor crawler network traffic while running
sudo python network_monitor.py -d 300 &
python main.py --workers 4
```

#### Comprehensive Analysis
```bash
# After crawling completes
python analyze_crawler_data.py
./crawler_utils.sh summarize_json_logs logs.json
./crawler_utils.sh check_redis_status
```

---

## File Structure

```
distributed-web-crawler/
├── models.py                    # SQLAlchemy ORM models
├── celery_app.py                 # Celery configuration
├── crawler_tasks.py              # Celery task definitions
├── analyze_crawler_data.py       # Data analysis script
├── network_monitor.py            # Network packet monitoring
├── crawler_utils.sh              # Shell utilities (executable)
├── scripts/
│   ├── db_sqlalchemy.py          # SQLAlchemy database operations
│   ├── general_crawler.py         # Enhanced with Celery integration
│   ├── standalone_worker.py      # Updated for SQLAlchemy
│   └── [existing scripts...]     # Unchanged for compatibility
├── [existing files...]           # All original files preserved
└── IMPLEMENTATION_GUIDE.md       # This document
```

---

## Dependencies

All new dependencies are already included in `requirements.txt`:
- `sqlalchemy==2.0.20` - ORM database operations
- `pymysql` - MySQL connector for SQLAlchemy
- `scapy` - Network packet analysis
- `celery==5.3.1` - Distributed task queue
- `pandas==2.0.3` - Data analysis
- `matplotlib==3.7.2` - Plotting and visualization
- `networkx==3.1` - Network graph analysis

---

## Conclusion

These 5 updates transform the distributed web crawler from a basic scraping system into a comprehensive, production-ready platform with:

1. **Professional Database Operations** (SQLAlchemy)
2. **Rich Data Analysis & Visualization** (Pandas/Matplotlib/NetworkX)
3. **Network-Level Monitoring** (Scapy)
4. **Scalable Task Distribution** (Celery)
5. **Powerful Shell Utilities** (curl/wget/awk/sed/jq)

All updates maintain full backward compatibility with the existing arXiv crawler while adding powerful new capabilities for general web crawling and analysis.
