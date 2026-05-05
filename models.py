"""
SQLAlchemy ORM models for the distributed web crawler
Replaces raw SQL queries with proper ORM models
"""

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, ForeignKey, Enum, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
import enum

Base = declarative_base()

# Enum for paper status
class PaperStatus(enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Paper(Base):
    """ORM model for papers table (general crawler)"""
    __tablename__ = 'papers'
    
    id = Column(Integer, primary_key=True)
    url = Column(String(2048), nullable=False, unique=True)
    title = Column(String(1000))
    content = Column(Text)
    content_hash = Column(String(64), unique=True)
    domain = Column(String(255))
    status = Column(Enum(PaperStatus), default=PaperStatus.QUEUED)
    priority = Column(Integer, default=50)
    crawl_date = Column(DateTime, default=func.now())
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    authors = relationship("PaperAuthor", back_populates="paper")
    keywords = relationship("PaperKeyword", back_populates="paper")
    subjects = relationship("PaperSubject", back_populates="paper")
    categories = relationship("PaperCategory", back_populates="paper")
    stats = relationship("PaperStats", back_populates="paper", uselist=False)
    discovered_links = relationship("DiscoveredLink", foreign_keys="DiscoveredLink.source_url", primaryjoin="DiscoveredLink.source_url==Paper.url")

class Author(Base):
    """ORM model for authors table"""
    __tablename__ = 'authors'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    
    # Relationships
    papers = relationship("PaperAuthor", back_populates="author")

class PaperAuthor(Base):
    """ORM model for paper_authors relationship table"""
    __tablename__ = 'paper_authors'
    
    paper_id = Column(Integer, ForeignKey('papers.id'), primary_key=True)
    author_id = Column(Integer, ForeignKey('authors.id'), primary_key=True)
    
    # Relationships
    paper = relationship("Paper", back_populates="authors")
    author = relationship("Author", back_populates="papers")

class Keyword(Base):
    """ORM model for keywords table"""
    __tablename__ = 'keywords'
    
    id = Column(Integer, primary_key=True)
    word = Column(String(100), nullable=False, unique=True)
    
    # Relationships
    papers = relationship("PaperKeyword", back_populates="keyword")

class PaperKeyword(Base):
    """ORM model for paper_keywords relationship table"""
    __tablename__ = 'paper_keywords'
    
    paper_id = Column(Integer, ForeignKey('papers.id'), primary_key=True)
    keyword_id = Column(Integer, ForeignKey('keywords.id'), primary_key=True)
    
    # Relationships
    paper = relationship("Paper", back_populates="keywords")
    keyword = relationship("Keyword", back_populates="papers")

class Subject(Base):
    """ORM model for subjects table"""
    __tablename__ = 'subjects'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    
    # Relationships
    papers = relationship("PaperSubject", back_populates="subject")

class PaperSubject(Base):
    """ORM model for paper_subjects relationship table"""
    __tablename__ = 'paper_subjects'
    
    paper_id = Column(Integer, ForeignKey('papers.id'), primary_key=True)
    subject_id = Column(Integer, ForeignKey('subjects.id'), primary_key=True)
    
    # Relationships
    paper = relationship("Paper", back_populates="subjects")
    subject = relationship("Subject", back_populates="papers")

class PaperStats(Base):
    """ORM model for paper_stats table"""
    __tablename__ = 'paper_stats'
    
    paper_id = Column(Integer, ForeignKey('papers.id'), primary_key=True)
    word_count = Column(Integer)
    content_length = Column(Integer)
    title_length = Column(Integer)
    num_authors = Column(Integer)
    num_keywords = Column(Integer)
    num_links = Column(Integer)
    
    # Relationships
    paper = relationship("Paper", back_populates="stats")

class DiscoveredLink(Base):
    """ORM model for discovered_links table"""
    __tablename__ = 'discovered_links'
    
    id = Column(Integer, primary_key=True)
    source_url = Column(String(2048), nullable=False)
    target_url = Column(String(2048), nullable=False)
    anchor_text = Column(String(500))
    discovered_date = Column(DateTime, default=func.now())

class Category(Base):
    """ORM model for categories table"""
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    
    # Relationships
    papers = relationship("PaperCategory", back_populates="category")

class PaperCategory(Base):
    """ORM model for paper_categories relationship table"""
    __tablename__ = 'paper_categories'
    
    paper_id = Column(Integer, ForeignKey('papers.id'), primary_key=True)
    category_id = Column(Integer, ForeignKey('categories.id'), primary_key=True)
    
    # Relationships
    paper = relationship("Paper", back_populates="categories")
    category = relationship("Category", back_populates="papers")

class CrawlerStats(Base):
    """ORM model for crawler_stats table"""
    __tablename__ = 'crawler_stats'
    
    id = Column(Integer, primary_key=True)
    stat_date = Column(DateTime, default=func.now())
    total_pages_crawled = Column(Integer, default=0)
    total_urls_discovered = Column(Integer, default=0)
    active_workers = Column(Integer, default=0)
    avg_response_time = Column(Float)
    error_count = Column(Integer, default=0)

class RobotsCache(Base):
    """ORM model for robots_cache table"""
    __tablename__ = 'robots_cache'
    
    domain = Column(String(255), primary_key=True)
    content = Column(Text)
    last_fetched = Column(DateTime, default=func.now())
    expires_at = Column(DateTime)

# Database session management
class DatabaseManager:
    """Manages SQLAlchemy database connections and sessions"""
    
    def __init__(self, database_url="mysql+pymysql://crawler_user:crawler_pass@localhost/crawler_db"):
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def get_session(self):
        """Get a new database session"""
        return self.SessionLocal()
    
    def create_tables(self):
        """Create all tables in the database"""
        Base.metadata.create_all(bind=self.engine)
    
    def drop_tables(self):
        """Drop all tables in the database"""
        Base.metadata.drop_all(bind=self.engine)

# Global database manager instance
db_manager = DatabaseManager()

def get_db_session():
    """Get a database session (dependency injection style)"""
    return db_manager.get_session()

# Legacy compatibility functions for arXiv database
class ArxivDatabaseManager:
    """Manages connections to the arXiv database for backward compatibility"""
    
    def __init__(self, database_url="mysql+pymysql://crawler_user:crawler_pass@localhost/arxiv_db"):
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def get_session(self):
        """Get a new arXiv database session"""
        return self.SessionLocal()
    
    def create_tables(self):
        """Create arXiv database tables"""
        ArxivBase.metadata.create_all(bind=self.engine)
    
    def drop_tables(self):
        """Drop arXiv database tables"""
        ArxivBase.metadata.drop_all(bind=self.engine)

# Legacy arXiv models (for backward compatibility)
ArxivBase = declarative_base()

class ArxivPaper(ArxivBase):
    """ORM model for arXiv papers table"""
    __tablename__ = 'papers'
    
    id = Column(Integer, primary_key=True)
    paper_id = Column(String(50), nullable=False, unique=True)
    title = Column(String(1000))
    abstract = Column(Text)
    primary_subject = Column(String(255))
    submission_info = Column(Text)
    url = Column(String(2048))
    
    # Relationships
    authors = relationship("ArxivPaperAuthor", back_populates="paper")
    subjects = relationship("ArxivPaperSubject", back_populates="paper")
    keywords = relationship("ArxivPaperKeyword", back_populates="paper")
    stats = relationship("ArxivPaperStats", back_populates="paper", uselist=False)

class ArxivAuthor(ArxivBase):
    """ORM model for arXiv authors table"""
    __tablename__ = 'authors'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    
    # Relationships
    papers = relationship("ArxivPaperAuthor", back_populates="author")

class ArxivPaperAuthor(ArxivBase):
    """ORM model for arXiv paper_authors relationship table"""
    __tablename__ = 'paper_authors'
    
    paper_id = Column(Integer, ForeignKey('papers.id'), primary_key=True)
    author_id = Column(Integer, ForeignKey('authors.id'), primary_key=True)
    
    # Relationships
    paper = relationship("ArxivPaper", back_populates="authors")
    author = relationship("ArxivAuthor", back_populates="papers")

class ArxivSubject(ArxivBase):
    """ORM model for arXiv subjects table"""
    __tablename__ = 'subjects'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    
    # Relationships
    papers = relationship("ArxivPaperSubject", back_populates="subject")

class ArxivPaperSubject(ArxivBase):
    """ORM model for arXiv paper_subjects relationship table"""
    __tablename__ = 'paper_subjects'
    
    paper_id = Column(Integer, ForeignKey('papers.id'), primary_key=True)
    subject_id = Column(Integer, ForeignKey('subjects.id'), primary_key=True)
    
    # Relationships
    paper = relationship("ArxivPaper", back_populates="subjects")
    subject = relationship("ArxivSubject", back_populates="papers")

class ArxivKeyword(ArxivBase):
    """ORM model for arXiv keywords table"""
    __tablename__ = 'keywords'
    
    id = Column(Integer, primary_key=True)
    word = Column(String(100), nullable=False, unique=True)
    
    # Relationships
    papers = relationship("ArxivPaperKeyword", back_populates="keyword")

class ArxivPaperKeyword(ArxivBase):
    """ORM model for arXiv paper_keywords relationship table"""
    __tablename__ = 'paper_keywords'
    
    paper_id = Column(Integer, ForeignKey('papers.id'), primary_key=True)
    keyword_id = Column(Integer, ForeignKey('keywords.id'), primary_key=True)
    
    # Relationships
    paper = relationship("ArxivPaper", back_populates="keywords")
    keyword = relationship("ArxivKeyword", back_populates="papers")

class ArxivPaperStats(ArxivBase):
    """ORM model for arXiv paper_stats table"""
    __tablename__ = 'paper_stats'
    
    paper_id = Column(Integer, ForeignKey('papers.id'), primary_key=True)
    word_count = Column(Integer)
    abstract_length = Column(Integer)
    title_length = Column(Integer)
    num_authors = Column(Integer)
    
    # Relationships
    paper = relationship("ArxivPaper", back_populates="stats")

# Global arXiv database manager instance
arxiv_db_manager = ArxivDatabaseManager()

def get_arxiv_db_session():
    """Get an arXiv database session"""
    return arxiv_db_manager.get_session()
