import json
import os
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

@dataclass
class DatabaseConfig:
    host: str = "localhost"
    port: int = 3306
    user: str = "crawler_user"
    password: str = "crawler_pass"
    database: str = "crawler_db"
    arxiv_database: str = "arxiv_db"

@dataclass
class RedisConfig:
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None

@dataclass
class CrawlerConfig:
    max_workers: int = 5
    request_timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    default_delay: float = 1.0
    max_depth: int = 3
    max_pages_per_domain: int = 1000
    user_agent: str = "DistributedCrawler/1.0 (educational project)"

@dataclass
class BloomFilterConfig:
    capacity: int = 1000000
    error_rate: float = 0.001

@dataclass
class QueueConfig:
    batch_size: int = 10
    max_queue_size: int = 100000
    priority_threshold_high: int = 30
    priority_threshold_medium: int = 70

@dataclass
class LoggingConfig:
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = None

@dataclass
class Config:
    database: DatabaseConfig
    redis: RedisConfig
    crawler: CrawlerConfig
    bloom_filter: BloomFilterConfig
    queue: QueueConfig
    logging: LoggingConfig
    
    # Domain-specific configurations
    domain_configs: Dict[str, Dict] = None
    
    # Keyword priorities
    strong_keywords: List[str] = None
    weak_keywords: List[str] = None
    
    def __post_init__(self):
        if self.domain_configs is None:
            self.domain_configs = {
                'wikipedia.org': {'delay': 1.0, 'priority_boost': -10},
                'github.com': {'delay': 2.0, 'priority_boost': -15},
                'stackoverflow.com': {'delay': 1.5, 'priority_boost': -10},
                'arxiv.org': {'delay': 3.0, 'priority_boost': -20},
                'medium.com': {'delay': 2.0, 'priority_boost': 0},
            }
        
        if self.strong_keywords is None:
            self.strong_keywords = [
                "llm", "large language model", "transformer",
                "deep learning", "neural network", "machine learning",
                "artificial intelligence", "api", "documentation",
                "tutorial", "guide"
            ]
        
        if self.weak_keywords is None:
            self.weak_keywords = [
                "nlp", "computer vision", "reinforcement learning",
                "blog", "article", "news", "research", "paper"
            ]

class ConfigManager:
    """Configuration management for the distributed crawler"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self) -> Config:
        """Load configuration from file or create default"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                
                # Create config from loaded data
                return Config(
                    database=DatabaseConfig(**data.get('database', {})),
                    redis=RedisConfig(**data.get('redis', {})),
                    crawler=CrawlerConfig(**data.get('crawler', {})),
                    bloom_filter=BloomFilterConfig(**data.get('bloom_filter', {})),
                    queue=QueueConfig(**data.get('queue', {})),
                    logging=LoggingConfig(**data.get('logging', {})),
                    domain_configs=data.get('domain_configs', {}),
                    strong_keywords=data.get('strong_keywords', []),
                    weak_keywords=data.get('weak_keywords', [])
                )
            except Exception as e:
                print(f"Error loading config file: {e}")
                print("Using default configuration")
        
        # Return default configuration
        return Config(
            database=DatabaseConfig(),
            redis=RedisConfig(),
            crawler=CrawlerConfig(),
            bloom_filter=BloomFilterConfig(),
            queue=QueueConfig(),
            logging=LoggingConfig()
        )
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            config_dict = asdict(self.config)
            
            with open(self.config_file, 'w') as f:
                json.dump(config_dict, f, indent=2)
            
            print(f"Configuration saved to {self.config_file}")
        except Exception as e:
            print(f"Error saving config file: {e}")
    
    def get_database_url(self) -> str:
        """Get database connection URL"""
        db = self.config.database
        return f"mysql://{db.user}:{db.password}@{db.host}:{db.port}/{db.database}"
    
    def get_arxiv_database_url(self) -> str:
        """Get arXiv database connection URL"""
        db = self.config.database
        return f"mysql://{db.user}:{db.password}@{db.host}:{db.port}/{db.arxiv_database}"
    
    def update_config(self, **kwargs):
        """Update configuration values"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
            else:
                print(f"Unknown config key: {key}")
    
    def get_domain_config(self, domain: str) -> Dict:
        """Get domain-specific configuration"""
        return self.config.domain_configs.get(domain, {
            'delay': self.config.crawler.default_delay,
            'priority_boost': 0
        })
    
    def calculate_priority(self, title: str, url: str = "") -> int:
        """Calculate priority based on title and URL"""
        title_lower = title.lower()
        url_lower = url.lower()
        
        score = 50  # Base score
        
        # Strong keywords
        for kw in self.config.strong_keywords:
            if kw in title_lower or kw in url_lower:
                score -= 20
        
        # Weak keywords
        for kw in self.config.weak_keywords:
            if kw in title_lower or kw in url_lower:
                score -= 10
        
        # Domain-specific boosts
        for domain, config in self.config.domain_configs.items():
            if domain in url_lower:
                score += config.get('priority_boost', 0)
                break
        
        return max(0, min(100, score))


# Global config instance
config_manager = ConfigManager()

def get_config() -> Config:
    """Get global configuration"""
    return config_manager.config

def update_config(**kwargs):
    """Update global configuration"""
    config_manager.update_config(**kwargs)

def save_config():
    """Save global configuration"""
    config_manager.save_config()
