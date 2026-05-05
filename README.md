# Distributed Web Crawler

A comprehensive distributed web crawler built with Python that can crawl multiple websites concurrently, handle duplicates, and extract structured data. This project features a **unified Celery-based architecture** with resilient database operations and professional task distribution.

## 🚀 **Current Status: FULLY OPERATIONAL**

The system has been completely refactored to use **Celery for task distribution** and **resilient database operations** that prevent transaction rollbacks. All critical bugs have been fixed.

## ✨ **Key Features**

### Core Architecture
- **🔄 Unified Celery Task Distribution**: Replaces fragmented manual Redis queues
- **🗄️ Resilient Database Operations**: String truncation + nested transactions prevent rollbacks
- **🌐 Distributed Crawling**: Multiple workers with proper URL routing
- **🔍 Smart Duplicate Detection**: Bloom filters with Redis-based storage
- **🤖 Robots.txt Compliance**: Centralized rate limiting and politeness policies
- **📊 Real-time Monitoring**: Structured logging and performance tracking

### Advanced Features
- **🎓 ArXiv Integration**: Specialized academic paper processing
- **📈 Data Analysis**: Visualization and insights generation
- **🌡️ Network Monitoring**: Real-time traffic analysis
- **⚙️ Configuration Management**: Centralized settings and environments
- **🛠️ Shell Utilities**: Comprehensive testing toolkit

## 🏗️ **Architecture Overview**

### **Primary Components (Celery-Based)**
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   main.py       │───▶│   celery_app.py  │───▶│ crawler_tasks.py│
│   (Producer)    │    │   (Task Router)  │    │   (Workers)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   seed.py       │    │   worker.py      │    │   Redis Queue   │
│   (Queue Init)  │    │   (Launcher)     │    │   (Tasks)       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### **Core Crawling System**
- **`crawler_tasks.py`**: ✅ **NEW** - Celery tasks for distributed crawling
- **`celery_app.py`**: ✅ **UPDATED** - Task routing and configuration
- **`worker.py`**: ✅ **REFACTORED** - Celery worker launcher (no more manual loops)
- **`main.py`**: ✅ **UPDATED** - Celery producer for task submission

### **Database Layer**
- **`models.py`**: ✅ **COMPLETE** - SQLAlchemy models for both databases
- **`db_sqlalchemy.py`**: ✅ **ENHANCED** - String truncation + resilient transactions
- **Legacy Support**: ✅ **MAINTAINED** - Backward compatibility for ArXiv

### **Utility Components**
- **`general_crawler.py`**: ✅ **WORKING** - Web page fetching and parsing
- **`bloom_filter.py`**: ✅ **WORKING** - Distributed duplicate detection
- **`robots.py`**: ✅ **WORKING** - Centralized rate limiting
- **`logger.py`**: ✅ **WORKING** - Structured logging system

## Installation

### Prerequisites

- Python 3.8+
- MySQL 5.7+
- Redis 6.0+

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd distributed-web-crawler
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up MySQL databases:
```bash
mysql -u root -p < schema.sql
```

5. Start Redis server:
```bash
redis-server
```

## 🚀 **Quick Start Guide**

### **Server Management**

#### **Start the System**
```bash
# 1. Start Redis (if not running)
redis-server

# 2. Start Celery Workers (run multiple instances for distributed crawling)
python worker.py --worker-id worker-1 &
python worker.py --worker-id worker-2 &
python worker.py --worker-id worker-3 &

# 3. Seed the queue with URLs
python seed.py --default

# 4. Start crawling (submit tasks)
python main.py --seeds "https://example.com" "https://httpbin.org/html" --no-monitor
```

#### **Stop the System**
```bash
# Stop all Celery workers
pkill -f "celery worker"

# Stop worker launchers
pkill -f "python worker.py"

# Clear Redis queues (optional)
redis-cli flushall
```

### **Production Deployment**

#### **Start Production Server**
```bash
# Start multiple workers with specific queues
python worker.py --queues crawling,arxiv --concurrency 8 --worker-id prod-worker-1 &

# Start monitoring (optional)
python main.py --monitor --daemon
```

#### **Monitor System Status**
```bash
# Check queue status
python seed.py --status

# Monitor Celery workers
celery -A celery_app inspect active

# View worker logs
tail -f celery.log
```

## 📋 **Usage Examples**

### **Basic Web Crawling**
```bash
# Crawl single URL
python main.py --seeds "https://example.com" --no-monitor

# Crawl multiple URLs
python main.py --seeds "https://example.com" "https://httpbin.org/html" --no-monitor

# Continuous crawling with monitoring
python main.py --seeds "https://example.com" --monitor
```

### **ArXiv Paper Processing**
```bash
# Process ArXiv papers
python main.py --seeds "https://arxiv.org/abs/2301.12345" --no-monitor

# Batch process ArXiv papers
python main.py --seeds "https://arxiv.org/list/cs.AI/recent" --no-monitor
```

### **Queue Management**
```bash
# Add URLs to high priority queue
python seed.py --url "https://example.com" --priority high

# Add multiple URLs to default queue
python seed.py --urls "url1" "url2" "url3" --priority default

# Load URLs from file
python seed.py --file urls.txt --priority default

# Clear all queues
python seed.py --clear

# View queue status
python seed.py --status
```

### **Worker Management**
```bash
# Start single worker
python worker.py --worker-id my-worker

# Start worker with specific queues
python worker.py --queues crawling --worker-id web-worker

# Start worker with custom concurrency
python worker.py --concurrency 8 --worker-id high-power-worker

# Start worker in daemon mode
python worker.py --daemon --worker-id daemon-worker
```

## 🔧 **Configuration**

### **Environment Variables**
```bash
# Redis Configuration
export CELERY_BROKER_URL=redis://localhost:6379/0
export CELERY_RESULT_BACKEND=rpc://

# Database Configuration
export DATABASE_URL=mysql+pymysql://crawler_user:crawler_pass@localhost/crawler_db
export ARXIV_DATABASE_URL=mysql+pymysql://crawler_user:crawler_pass@localhost/arxiv_db
```

### **Custom Configuration**
Edit `scripts/config.py` to modify:
- Redis connection settings
- Database connection parameters
- Crawling behavior and delays
- Logging levels and outputs
- Rate limiting policies
```

## 🔍 **Monitoring & Troubleshooting**

### **System Health Checks**
```bash
# Check Redis connectivity
redis-cli ping

# Check database connections
python -c "from models import get_db_session; print('Database OK')"

# Check Celery workers
celery -A celery_app inspect active
celery -A celery_app inspect stats
```

### **Common Issues & Solutions**

#### **🚨 Worker Not Starting**
```bash
# Check if Redis is running
redis-cli ping

# Check Celery configuration
python -c "from celery_app import app; print('Celery OK')"

# Start worker with debug output
python worker.py --worker-id debug-worker --loglevel debug
```

#### **🚨 Tasks Not Processing**
```bash
# Check queue status
python seed.py --status

# Clear stuck tasks
redis-cli flushall

# Restart workers
pkill -f "celery worker"
python worker.py --worker-id fresh-worker &
```

#### **🚨 Database Insertion Failures**
```bash
# Check database connectivity
python -c "from models import get_db_session; session = get_db_session(); print('DB OK')"

# Verify database schema
mysql -u root -e "SHOW TABLES FROM crawler_db;"
mysql -u root -e "SHOW TABLES FROM arxiv_db;"

# Check for duplicate content
mysql -u root -e "SELECT url, COUNT(*) as count FROM crawler_db.papers GROUP BY url HAVING count > 1;"
```

#### **� Memory Issues**
```bash
# Monitor Redis memory
redis-cli info memory

# Clear Bloom filter (if too large)
redis-cli del bloom_filter:urls

# Restart with limited memory
python worker.py --concurrency 2 --worker-id low-memory-worker
```

### **Performance Optimization**

#### **High-Performance Configuration**
```bash
# Start optimized workers
python worker.py --concurrency 16 --prefetch-multiplier 4 --worker-id perf-worker

# Use Redis cluster (if available)
export CELERY_BROKER_URL=redis://redis-cluster:6379/0
```

#### **Database Optimization**
```bash
# Add indexes to improve performance
mysql -u root -e "
USE crawler_db;
CREATE INDEX idx_papers_url ON papers(url);
CREATE INDEX idx_papers_content_hash ON papers(content_hash);
CREATE INDEX idx_papers_crawl_date ON papers(crawl_date);
"
```

## 📊 **Data Analysis & Monitoring**

### **View Crawled Data**
```bash
# Check crawled papers count
mysql -u root -e "USE crawler_db; SELECT COUNT(*) as total_papers FROM papers;"

# View recent crawls
mysql -u root -e "USE crawler_db; SELECT url, title, crawl_date FROM papers ORDER BY crawl_date DESC LIMIT 10;"

# Check crawler performance
mysql -u root -e "USE crawler_db; SELECT * FROM crawler_stats ORDER BY stat_date DESC LIMIT 5;"
```

### **Generate Reports**
```bash
# Run data analysis
python analyze_crawler_data.py

# Generate visualization
python visualize_crawler_data.py

# Network analysis
python network_monitor.py --analyze
```

## 🔄 **Legacy Compatibility**

### **ArXiv Crawler (Legacy)**
```bash
# Legacy ArXiv producer (still functional)
python scripts/producer.py

# Legacy ArXiv worker (still functional)  
python scripts/worker.py
```

### **Simple Crawler (Testing)**
```bash
# For testing purposes only
python simple_crawler.py 1
```

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with the provided utilities
5. Submit a pull request

## 📄 **License**

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 **Support**

For issues and questions:
- Check the troubleshooting section above
- Review the implementation guide
- Check the Celery and Redis documentation
- Open an issue on GitHub

### Configuration

Create a `config.json` file to customize settings:

```json
{
  "database": {
    "host": "localhost",
    "port": 3306,
    "user": "crawler_user",
    "password": "crawler_pass",
    "database": "crawler_db"
  },
  "redis": {
    "host": "localhost",
    "port": 6379,
    "db": 0
  },
  "crawler": {
    "max_workers": 5,
    "request_timeout": 30,
    "max_retries": 3,
    "default_delay": 1.0
  },
  "queue": {
    "batch_size": 10,
    "max_queue_size": 100000
  }
}
```

## Project Structure

```
Distriubuted-Web-Crawler/
├── main.py                 # Main orchestrator
├── requirements.txt        # Python dependencies
├── schema.sql             # Database schema
├── README.md              # This file
├── config.json            # Configuration file (create as needed)
└── scripts/               # Core modules
    ├── config.py          # Configuration management
    ├── general_crawler.py # General web crawler
    ├── url_queue.py       # URL queue management
    ├── bloom_filter.py    # Duplicate detection
    ├── robots.py          # robots.txt handling
    ├── logger.py          # Logging system
    ├── producer.py        # ArXiv producer (legacy)
    ├── worker.py          # ArXiv worker (legacy)
    ├── utils.py           # Utility functions
    └── db.py              # Database operations
```

## Monitoring

The crawler provides real-time monitoring through:

- **Console Dashboard**: Shows queue status, active workers, and statistics
- **Redis Logs**: Detailed logs stored in Redis for analysis
- **Performance Metrics**: Track crawl times and system performance

### Dashboard Output

```
============================================================
DISTRIBUTED CRAWLER DASHBOARD
============================================================
Active Workers: 5
Queue Size: 1247
  - High Priority: 23
  - Medium Priority: 456
  - Low Priority: 768
Pages Crawled: 5234
Errors: 12
Active Domains: 45
============================================================
```

## API Reference

### Main Classes

#### DistributedCrawler
Main orchestrator class that manages the entire system.

#### GeneralWebCrawler
Handles web page fetching, parsing, and data extraction.

#### URLQueue
Manages priority-based URL queuing with Redis.

#### BloomFilter
Provides efficient duplicate detection.

#### RobotsCache
Handles robots.txt parsing and caching.

## Database Schema

The system uses two databases:

1. **crawler_db**: General web crawling data
2. **arxiv_db**: Legacy arXiv paper data

### Main Tables

- `papers`: Crawled page information
- `keywords`: Extracted keywords
- `paper_keywords`: Link between papers and keywords
- `discovered_links`: Links found during crawling
- `crawler_stats`: System statistics

## Performance Considerations

- **Memory Usage**: Bloom filters use ~10MB for 1M URLs
- **Redis Memory**: Queue and logs stored in Redis
- **Database Storage**: Content and metadata in MySQL
- **Network**: Respects robots.txt and rate limits

## Troubleshooting

### Common Issues

1. **Redis Connection Error**:
   - Ensure Redis is running: `redis-server`
   - Check Redis configuration in `config.json`

2. **Database Connection Error**:
   - Verify MySQL is running
   - Check database credentials
   - Run schema setup: `mysql -u root -p < schema.sql`

3. **Permission Errors**:
   - Check robots.txt compliance
   - Verify rate limiting settings

### Debug Mode

Enable debug logging:

```json
{
  "logging": {
    "level": "DEBUG"
  }
}
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is for educational purposes. Please respect website terms of service and robots.txt files.

## Advanced Features

### Custom Content Extractors

The system supports specialized content extraction for different page types:

```python
from scripts.general_crawler import ContentExtractor

# Extract article content
article_data = ContentExtractor.extract_article(soup, url)

# Extract product information
product_data = ContentExtractor.extract_product(soup, url)
```

### Custom Priority Calculation

Implement custom priority logic:

```python
from scripts.url_queue import PriorityCalculator

calculator = PriorityCalculator()
priority = calculator.calculate_priority(url, title, content)
```

### Distributed Deployment

For large-scale deployment:

1. Use Redis Cluster for distributed queuing
2. Deploy workers across multiple machines
3. Use load balancer for Redis connections
4. Implement monitoring with Prometheus/Grafana

## Shell Tools Integration

The crawler integrates with standard shell tools:

```bash
# Test URLs with curl
curl -I https://example.com

# Process logs with awk
awk '/ERROR/ {print $0}' crawler.log

# Extract JSON data with jq
jq '.stats' dashboard.json
```

## Future Enhancements

- [ ] Web-based monitoring dashboard
- [ ] Machine learning for content classification
- [ ] Distributed file system support
- [ ] API for external integrations
- [ ] Docker containerization
- [ ] Kubernetes deployment manifests


🛑 Stop Redis
brew services stop redis
🛑 Stop MySQL
brew services stop mysql