-- Distributed Web Crawler Database Schema
-- MySQL database setup for the crawler system

CREATE DATABASE IF NOT EXISTS crawler_db;
USE crawler_db;

-- Papers table (generalized from arXiv papers)
CREATE TABLE IF NOT EXISTS papers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    url VARCHAR(2048) NOT NULL,
    title VARCHAR(1000),
    content TEXT,
    content_hash VARCHAR(64) UNIQUE,
    domain VARCHAR(255),
    status ENUM('queued', 'processing', 'completed', 'failed') DEFAULT 'queued',
    priority INT DEFAULT 50,
    crawl_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_url (url(255)),
    INDEX idx_status (status),
    INDEX idx_domain (domain),
    INDEX idx_priority (priority),
    INDEX idx_crawl_date (crawl_date)
);

-- Authors table (generalized)
CREATE TABLE IF NOT EXISTS authors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    INDEX idx_name (name)
);

-- Link papers and authors
CREATE TABLE IF NOT EXISTS paper_authors (
    paper_id INT,
    author_id INT,
    PRIMARY KEY (paper_id, author_id),
    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE,
    FOREIGN KEY (author_id) REFERENCES authors(id) ON DELETE CASCADE
);

-- Keywords/Tags table
CREATE TABLE IF NOT EXISTS keywords (
    id INT AUTO_INCREMENT PRIMARY KEY,
    word VARCHAR(100) NOT NULL UNIQUE,
    INDEX idx_word (word)
);

-- Link papers and keywords
CREATE TABLE IF NOT EXISTS paper_keywords (
    paper_id INT,
    keyword_id INT,
    PRIMARY KEY (paper_id, keyword_id),
    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE,
    FOREIGN KEY (keyword_id) REFERENCES keywords(id) ON DELETE CASCADE
);

-- Categories/Subjects table
CREATE TABLE IF NOT EXISTS categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    INDEX idx_name (name)
);

-- Link papers and categories
CREATE TABLE IF NOT EXISTS paper_categories (
    paper_id INT,
    category_id INT,
    PRIMARY KEY (paper_id, category_id),
    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
);

-- Paper statistics
CREATE TABLE IF NOT EXISTS paper_stats (
    paper_id INT PRIMARY KEY,
    word_count INT,
    content_length INT,
    title_length INT,
    num_authors INT,
    num_keywords INT,
    num_links INT,
    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
);

-- Links found in pages (for crawling)
CREATE TABLE IF NOT EXISTS discovered_links (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_url VARCHAR(2048) NOT NULL,
    target_url VARCHAR(2048) NOT NULL,
    anchor_text VARCHAR(500),
    discovered_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_source (source_url(255)),
    INDEX idx_target (target_url(255)),
    INDEX idx_discovered_date (discovered_date)
);

-- Crawler statistics and monitoring
CREATE TABLE IF NOT EXISTS crawler_stats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stat_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_pages_crawled INT DEFAULT 0,
    total_urls_discovered INT DEFAULT 0,
    active_workers INT DEFAULT 0,
    avg_response_time DECIMAL(10,3),
    error_count INT DEFAULT 0,
    INDEX idx_stat_date (stat_date)
);

-- Robots.txt cache
CREATE TABLE IF NOT EXISTS robots_cache (
    domain VARCHAR(255) PRIMARY KEY,
    content TEXT,
    last_fetched TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    INDEX idx_expires (expires_at)
);

-- Legacy arXiv specific tables (keep for backward compatibility)
CREATE DATABASE IF NOT EXISTS arxiv_db;
USE arxiv_db;

CREATE TABLE IF NOT EXISTS papers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    paper_id VARCHAR(50) NOT NULL UNIQUE,
    title VARCHAR(1000),
    abstract TEXT,
    primary_subject VARCHAR(255),
    submission_info TEXT,
    url VARCHAR(2048),
    INDEX idx_paper_id (paper_id)
);

CREATE TABLE IF NOT EXISTS authors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    INDEX idx_name (name)
);

CREATE TABLE IF NOT EXISTS paper_authors (
    paper_id INT,
    author_id INT,
    PRIMARY KEY (paper_id, author_id),
    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE,
    FOREIGN KEY (author_id) REFERENCES authors(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS subjects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    INDEX idx_name (name)
);

CREATE TABLE IF NOT EXISTS paper_subjects (
    paper_id INT,
    subject_id INT,
    PRIMARY KEY (paper_id, subject_id),
    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS keywords (
    id INT AUTO_INCREMENT PRIMARY KEY,
    word VARCHAR(100) NOT NULL UNIQUE,
    INDEX idx_word (word)
);

CREATE TABLE IF NOT EXISTS paper_keywords (
    paper_id INT,
    keyword_id INT,
    PRIMARY KEY (paper_id, keyword_id),
    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE,
    FOREIGN KEY (keyword_id) REFERENCES keywords(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS paper_stats (
    paper_id INT PRIMARY KEY,
    word_count INT,
    abstract_length INT,
    title_length INT,
    num_authors INT,
    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
);

-- Create user for the crawler
CREATE USER IF NOT EXISTS 'crawler_user'@'localhost' IDENTIFIED BY 'crawler_pass';
GRANT ALL PRIVILEGES ON crawler_db.* TO 'crawler_user'@'localhost';
GRANT ALL PRIVILEGES ON arxiv_db.* TO 'crawler_user'@'localhost';
FLUSH PRIVILEGES;
