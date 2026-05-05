# Distributed Web Crawler

A comprehensive distributed web crawler built with Python that can crawl multiple websites concurrently, handle duplicates, and extract structured data.

## Features

- **Distributed Architecture**: Multiple crawler workers for concurrent processing
- **URL Management**: Priority-based queue system with Redis
- **Duplicate Detection**: Efficient duplicate detection using Bloom filters
- **Data Extraction**: Parse and store structured information from web pages
- **Rate Limiting**: Respect robots.txt and politeness policies
- **Real-time Monitoring**: Live dashboard and logging system
- **ArXiv Integration**: Legacy support for academic paper crawling

## Architecture

### Core Components

1. **Main Orchestrator** (`main.py`): Manages the entire distributed system
2. **URL Queue** (`scripts/url_queue.py`): Priority-based URL management
3. **General Crawler** (`scripts/general_crawler.py`): Web page fetching and parsing
4. **Bloom Filter** (`scripts/bloom_filter.py`): Efficient duplicate detection
5. **Robots Handler** (`scripts/robots.py`): robots.txt compliance and rate limiting
6. **Configuration** (`scripts/config.py`): Centralized configuration management
7. **Logger** (`scripts/logger.py`): Structured logging and monitoring

### Legacy ArXiv Components

- **Producer** (`scripts/producer.py`): Fetches arXiv paper listings
- **Worker** (`scripts/worker.py`): Processes arXiv papers
- **Database** (`scripts/db.py`): ArXiv-specific database operations

## Installation

### Prerequisites

- Python 3.8+
- MySQL 5.7+
- Redis 6.0+

### Setup

1. **Clone the repository**:
```bash
git clone <repository-url>
cd Distriubuted-Web-Crawler
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Setup MySQL database**:
```bash
mysql -u root -p < schema.sql
```

4. **Start Redis**:
```bash
redis-server
```

## Usage

### Basic Usage

Run the distributed crawler with default settings:

```bash
python main.py
```

### Advanced Usage

```bash
# Custom configuration
python main.py --config config.json

# Specify number of workers
python main.py --workers 8

# Provide seed URLs
python main.py --seeds https://example.com https://another-site.com

# Run arXiv crawler only
python main.py --arxiv

# Disable monitoring dashboard
python main.py --no-monitor

# Setup database schema
python main.py --setup-db
```

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