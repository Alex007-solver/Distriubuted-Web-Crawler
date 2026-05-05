"""
SQLAlchemy-based database operations for the distributed web crawler
Replaces the original db.py with ORM-based operations
"""

from models import (
    get_arxiv_db_session, get_db_session,
    ArxivPaper, ArxivAuthor, ArxivPaperAuthor, ArxivSubject, ArxivPaperSubject,
    ArxivKeyword, ArxivPaperKeyword, ArxivPaperStats,
    Paper, Author, PaperAuthor, Subject, PaperSubject, Keyword, PaperKeyword,
    PaperStats, DiscoveredLink, CrawlerStats
)
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# ==================== LEGACY ARXIV FUNCTIONS (for backward compatibility) ====================

def insert_arxiv_paper(paper_data: Dict) -> Optional[int]:
    """Insert or update an arXiv paper using SQLAlchemy"""
    session = get_arxiv_db_session()
    try:
        # Check if paper already exists
        existing_paper = session.query(ArxivPaper).filter_by(paper_id=paper_data["paper_id"]).first()
        
        if existing_paper:
            # Update existing paper
            existing_paper.title = paper_data.get("title", existing_paper.title)
            existing_paper.abstract = paper_data.get("abstract", existing_paper.abstract)
            existing_paper.primary_subject = paper_data.get("primary_subject", existing_paper.primary_subject)
            existing_paper.submission_info = paper_data.get("submission_info", existing_paper.submission_info)
            existing_paper.url = paper_data.get("url", existing_paper.url)
            paper_id = existing_paper.id
        else:
            # Create new paper
            new_paper = ArxivPaper(
                paper_id=paper_data["paper_id"],
                title=paper_data.get("title", ""),
                abstract=paper_data.get("abstract", ""),
                primary_subject=paper_data.get("primary_subject", ""),
                submission_info=paper_data.get("submission_info", ""),
                url=paper_data.get("url", "")
            )
            session.add(new_paper)
            session.flush()  # Get the ID without committing
            paper_id = new_paper.id
        
        session.commit()
        logger.debug(f"Inserted/updated arXiv paper {paper_data['paper_id']} with ID {paper_id}")
        return paper_id
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error inserting arXiv paper {paper_data.get('paper_id', 'unknown')}: {e}")
        raise
    finally:
        session.close()

def insert_arxiv_author(name: str) -> Optional[int]:
    """Insert or update an arXiv author using SQLAlchemy"""
    session = get_arxiv_db_session()
    try:
        # Check if author already exists
        existing_author = session.query(ArxivAuthor).filter_by(name=name).first()
        
        if existing_author:
            author_id = existing_author.id
        else:
            # Create new author
            new_author = ArxivAuthor(name=name)
            session.add(new_author)
            session.flush()
            author_id = new_author.id
        
        session.commit()
        logger.debug(f"Inserted/updated arXiv author '{name}' with ID {author_id}")
        return author_id
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error inserting arXiv author '{name}': {e}")
        raise
    finally:
        session.close()

def link_arxiv_paper_author(paper_id: int, author_id: int) -> bool:
    """Link an arXiv paper to an author"""
    session = get_arxiv_db_session()
    try:
        # Check if link already exists
        existing_link = session.query(ArxivPaperAuthor).filter_by(
            paper_id=paper_id, author_id=author_id
        ).first()
        
        if not existing_link:
            # Create new link
            new_link = ArxivPaperAuthor(paper_id=paper_id, author_id=author_id)
            session.add(new_link)
            session.commit()
            logger.debug(f"Linked arXiv paper {paper_id} to author {author_id}")
        
        return True
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error linking arXiv paper {paper_id} to author {author_id}: {e}")
        return False
    finally:
        session.close()

def insert_arxiv_subject(name: str) -> Optional[int]:
    """Insert or update an arXiv subject using SQLAlchemy"""
    session = get_arxiv_db_session()
    try:
        # Check if subject already exists
        existing_subject = session.query(ArxivSubject).filter_by(name=name).first()
        
        if existing_subject:
            subject_id = existing_subject.id
        else:
            # Create new subject
            new_subject = ArxivSubject(name=name)
            session.add(new_subject)
            session.flush()
            subject_id = new_subject.id
        
        session.commit()
        logger.debug(f"Inserted/updated arXiv subject '{name}' with ID {subject_id}")
        return subject_id
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error inserting arXiv subject '{name}': {e}")
        raise
    finally:
        session.close()

def link_arxiv_paper_subject(paper_id: int, subject_id: int) -> bool:
    """Link an arXiv paper to a subject"""
    session = get_arxiv_db_session()
    try:
        # Check if link already exists
        existing_link = session.query(ArxivPaperSubject).filter_by(
            paper_id=paper_id, subject_id=subject_id
        ).first()
        
        if not existing_link:
            # Create new link
            new_link = ArxivPaperSubject(paper_id=paper_id, subject_id=subject_id)
            session.add(new_link)
            session.commit()
            logger.debug(f"Linked arXiv paper {paper_id} to subject {subject_id}")
        
        return True
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error linking arXiv paper {paper_id} to subject {subject_id}: {e}")
        return False
    finally:
        session.close()

def insert_arxiv_keyword(word: str) -> Optional[int]:
    """Insert or update an arXiv keyword using SQLAlchemy"""
    session = get_arxiv_db_session()
    try:
        # Check if keyword already exists
        existing_keyword = session.query(ArxivKeyword).filter_by(word=word).first()
        
        if existing_keyword:
            keyword_id = existing_keyword.id
        else:
            # Create new keyword
            new_keyword = ArxivKeyword(word=word)
            session.add(new_keyword)
            session.flush()
            keyword_id = new_keyword.id
        
        session.commit()
        logger.debug(f"Inserted/updated arXiv keyword '{word}' with ID {keyword_id}")
        return keyword_id
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error inserting arXiv keyword '{word}': {e}")
        raise
    finally:
        session.close()

def link_arxiv_paper_keyword(paper_id: int, keyword_id: int) -> bool:
    """Link an arXiv paper to a keyword"""
    session = get_arxiv_db_session()
    try:
        # Check if link already exists
        existing_link = session.query(ArxivPaperKeyword).filter_by(
            paper_id=paper_id, keyword_id=keyword_id
        ).first()
        
        if not existing_link:
            # Create new link
            new_link = ArxivPaperKeyword(paper_id=paper_id, keyword_id=keyword_id)
            session.add(new_link)
            session.commit()
            logger.debug(f"Linked arXiv paper {paper_id} to keyword {keyword_id}")
        
        return True
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error linking arXiv paper {paper_id} to keyword {keyword_id}: {e}")
        return False
    finally:
        session.close()

def insert_arxiv_stats(paper_id: int, stats: Dict) -> bool:
    """Insert or update arXiv paper statistics"""
    session = get_arxiv_db_session()
    try:
        # Check if stats already exist
        existing_stats = session.query(ArxivPaperStats).filter_by(paper_id=paper_id).first()
        
        if existing_stats:
            # Update existing stats
            existing_stats.word_count = stats.get("word_count", existing_stats.word_count)
            existing_stats.abstract_length = stats.get("abstract_length", existing_stats.abstract_length)
            existing_stats.title_length = stats.get("title_length", existing_stats.title_length)
            existing_stats.num_authors = stats.get("num_authors", existing_stats.num_authors)
        else:
            # Create new stats
            new_stats = ArxivPaperStats(
                paper_id=paper_id,
                word_count=stats.get("word_count", 0),
                abstract_length=stats.get("abstract_length", 0),
                title_length=stats.get("title_length", 0),
                num_authors=stats.get("num_authors", 0)
            )
            session.add(new_stats)
        
        session.commit()
        logger.debug(f"Inserted/updated arXiv stats for paper {paper_id}")
        return True
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error inserting arXiv stats for paper {paper_id}: {e}")
        return False
    finally:
        session.close()

# ==================== GENERAL CRAWLER FUNCTIONS (new SQLAlchemy-based) ====================

def insert_paper(paper_data: Dict) -> Optional[int]:
    """Insert or update a general paper using SQLAlchemy"""
    session = get_db_session()
    try:
        # Check if paper already exists by URL or content_hash
        existing_paper = session.query(Paper).filter(
            (Paper.url == paper_data["url"]) | 
            (Paper.content_hash == paper_data.get("content_hash"))
        ).first()
        
        if existing_paper:
            # Update existing paper
            for key, value in paper_data.items():
                if hasattr(existing_paper, key):
                    setattr(existing_paper, key, value)
            paper_id = existing_paper.id
        else:
            # Create new paper
            new_paper = Paper(**paper_data)
            session.add(new_paper)
            session.flush()
            paper_id = new_paper.id
        
        session.commit()
        logger.debug(f"Inserted/updated paper {paper_data.get('url', 'unknown')} with ID {paper_id}")
        return paper_id
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error inserting paper {paper_data.get('url', 'unknown')}: {e}")
        raise
    finally:
        session.close()

def insert_author(name: str) -> Optional[int]:
    """Insert or update an author using SQLAlchemy"""
    session = get_db_session()
    try:
        existing_author = session.query(Author).filter_by(name=name).first()
        
        if existing_author:
            author_id = existing_author.id
        else:
            new_author = Author(name=name)
            session.add(new_author)
            session.flush()
            author_id = new_author.id
        
        session.commit()
        logger.debug(f"Inserted/updated author '{name}' with ID {author_id}")
        return author_id
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error inserting author '{name}': {e}")
        raise
    finally:
        session.close()

def link_paper_author(paper_id: int, author_id: int) -> bool:
    """Link a paper to an author"""
    session = get_db_session()
    try:
        existing_link = session.query(PaperAuthor).filter_by(
            paper_id=paper_id, author_id=author_id
        ).first()
        
        if not existing_link:
            new_link = PaperAuthor(paper_id=paper_id, author_id=author_id)
            session.add(new_link)
            session.commit()
            logger.debug(f"Linked paper {paper_id} to author {author_id}")
        
        return True
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error linking paper {paper_id} to author {author_id}: {e}")
        return False
    finally:
        session.close()

def insert_keyword(word: str) -> Optional[int]:
    """Insert or update a keyword using SQLAlchemy"""
    session = get_db_session()
    try:
        existing_keyword = session.query(Keyword).filter_by(word=word).first()
        
        if existing_keyword:
            keyword_id = existing_keyword.id
        else:
            new_keyword = Keyword(word=word)
            session.add(new_keyword)
            session.flush()
            keyword_id = new_keyword.id
        
        session.commit()
        logger.debug(f"Inserted/updated keyword '{word}' with ID {keyword_id}")
        return keyword_id
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error inserting keyword '{word}': {e}")
        raise
    finally:
        session.close()

def link_paper_keyword(paper_id: int, keyword_id: int) -> bool:
    """Link a paper to a keyword"""
    session = get_db_session()
    try:
        existing_link = session.query(PaperKeyword).filter_by(
            paper_id=paper_id, keyword_id=keyword_id
        ).first()
        
        if not existing_link:
            new_link = PaperKeyword(paper_id=paper_id, keyword_id=keyword_id)
            session.add(new_link)
            session.commit()
            logger.debug(f"Linked paper {paper_id} to keyword {keyword_id}")
        
        return True
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error linking paper {paper_id} to keyword {keyword_id}: {e}")
        return False
    finally:
        session.close()

def insert_stats(paper_id: int, stats: Dict) -> bool:
    """Insert or update paper statistics"""
    session = get_db_session()
    try:
        existing_stats = session.query(PaperStats).filter_by(paper_id=paper_id).first()
        
        if existing_stats:
            for key, value in stats.items():
                if hasattr(existing_stats, key):
                    setattr(existing_stats, key, value)
        else:
            new_stats = PaperStats(paper_id=paper_id, **stats)
            session.add(new_stats)
        
        session.commit()
        logger.debug(f"Inserted/updated stats for paper {paper_id}")
        return True
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error inserting stats for paper {paper_id}: {e}")
        return False
    finally:
        session.close()

def insert_discovered_link(source_url: str, target_url: str, anchor_text: str = "") -> bool:
    """Insert a discovered link"""
    session = get_db_session()
    try:
        new_link = DiscoveredLink(
            source_url=source_url,
            target_url=target_url,
            anchor_text=anchor_text
        )
        session.add(new_link)
        session.commit()
        logger.debug(f"Inserted discovered link: {source_url} -> {target_url}")
        return True
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error inserting discovered link: {e}")
        return False
    finally:
        session.close()

def update_crawler_stats(stats: Dict) -> bool:
    """Update crawler statistics"""
    session = get_db_session()
    try:
        new_stats = CrawlerStats(**stats)
        session.add(new_stats)
        session.commit()
        logger.debug("Updated crawler statistics")
        return True
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating crawler stats: {e}")
        return False
    finally:
        session.close()

# ==================== LEGACY COMPATIBILITY WRAPPERS ====================

# Map old function names to new SQLAlchemy functions for backward compatibility
def get_connection():
    """Legacy compatibility - returns session instead of connection"""
    return get_arxiv_db_session()

def insert_paper_legacy(cursor, paper):
    """Legacy wrapper for insert_arxiv_paper"""
    return insert_arxiv_paper(paper)

def insert_author_legacy(cursor, name):
    """Legacy wrapper for insert_arxiv_author"""
    return insert_arxiv_author(name)

def link_paper_author_legacy(cursor, paper_id, author_id):
    """Legacy wrapper for link_arxiv_paper_author"""
    return link_arxiv_paper_author(paper_id, author_id)

def insert_subject_legacy(cursor, name):
    """Legacy wrapper for insert_arxiv_subject"""
    return insert_arxiv_subject(name)

def link_paper_subject_legacy(cursor, paper_id, subject_id):
    """Legacy wrapper for link_arxiv_paper_subject"""
    return link_arxiv_paper_subject(paper_id, subject_id)

def insert_keyword_legacy(cursor, word):
    """Legacy wrapper for insert_arxiv_keyword"""
    return insert_arxiv_keyword(word)

def link_paper_keyword_legacy(cursor, paper_id, keyword_id):
    """Legacy wrapper for link_arxiv_paper_keyword"""
    return link_arxiv_paper_keyword(paper_id, keyword_id)

def insert_stats_legacy(cursor, paper_id, stats):
    """Legacy wrapper for insert_arxiv_stats"""
    return insert_arxiv_stats(paper_id, stats)
