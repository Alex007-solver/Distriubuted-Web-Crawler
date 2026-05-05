import requests
import time
import hashlib
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from collections import Counter
import re
import logging
from fake_useragent import UserAgent
from robots import check_robots_and_wait
from bloom_filter import DuplicateDetector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeneralWebCrawler:
    """General purpose web crawler with advanced features"""
    
    def __init__(self, redis_client, config=None):
        self.r = redis_client
        self.config = config or {}
        self.ua = UserAgent()
        self.duplicate_detector = DuplicateDetector(redis_client)
        
        # Default headers
        self.headers = {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        # Content extraction patterns
        self.title_selectors = [
            'title',
            'h1',
            '.title',
            '#title',
            '[property="og:title"]',
            '[name="title"]'
        ]
        
        self.content_selectors = [
            'article',
            'main',
            '.content',
            '#content',
            '.post-content',
            '.article-content',
            '[property="og:description"]',
            '[name="description"]'
        ]
    
    def fetch_page(self, url, timeout=30):
        """Fetch a web page with proper headers and error handling"""
        try:
            # Check robots.txt and rate limiting
            if not check_robots_and_wait(url, self.r):
                return None
            
            # Update User-Agent for each request
            self.headers['User-Agent'] = self.ua.random
            
            logger.info(f"Fetching: {url}")
            response = requests.get(url, headers=self.headers, timeout=timeout)
            response.raise_for_status()
            
            return response
            
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def extract_links(self, soup, base_url):
        """Extract all valid links from a page"""
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href'].strip()
            
            # Skip empty, javascript, mailto, tel links
            if not href or href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                continue
            
            # Convert relative URLs to absolute
            absolute_url = urljoin(base_url, href)
            
            # Only include HTTP/HTTPS URLs
            if absolute_url.startswith(('http://', 'https://')):
                links.append({
                    'url': absolute_url,
                    'anchor_text': link.get_text(strip=True)[:200]  # Limit anchor text length
                })
        
        return links
    
    def extract_title(self, soup):
        """Extract page title using multiple strategies"""
        for selector in self.title_selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get_text(strip=True)
                if title and len(title) > 5:  # Filter out very short titles
                    return title
        
        return "Untitled"
    
    def extract_content(self, soup):
        """Extract main content from a page"""
        for selector in self.content_selectors:
            element = soup.select_one(selector)
            if element:
                content = element.get_text(strip=True)
                if len(content) > 100:  # Filter out very short content
                    return content
        
        # Fallback to body text
        body = soup.find('body')
        if body:
            return body.get_text(strip=True)
        
        return ""
    
    def extract_metadata(self, soup, url):
        """Extract metadata from page"""
        metadata = {}
        
        # Basic meta tags
        for meta in soup.find_all('meta'):
            name = meta.get('name') or meta.get('property')
            content = meta.get('content')
            
            if name and content:
                metadata[name.lower()] = content
        
        # Domain information
        parsed_url = urlparse(url)
        metadata['domain'] = parsed_url.netloc
        metadata['path'] = parsed_url.path
        
        # Page language
        html_tag = soup.find('html')
        if html_tag and html_tag.get('lang'):
            metadata['language'] = html_tag.get('lang')
        
        return metadata
    
    def extract_keywords(self, text, top_n=10):
        """Extract keywords from text content"""
        # Common English stopwords
        stopwords = set([
            "the", "and", "is", "in", "to", "of", "for", "with", "on", "this", 
            "that", "we", "by", "an", "be", "are", "as", "from", "was", "were",
            "will", "would", "could", "should", "may", "might", "can", "has", "have",
            "had", "been", "being", "or", "but", "not", "at", "it", "they", "their",
            "them", "his", "her", "its", "our", "us", "your", "you", "i", "me", "my"
        ])
        
        # Extract words (4+ characters)
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        words = [w for w in words if w not in stopwords]
        
        # Count frequency and return top keywords
        freq = Counter(words)
        return [w for w, _ in freq.most_common(top_n)]
    
    def compute_content_hash(self, content):
        """Compute hash for content to detect duplicates"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def crawl_page(self, url):
        """Main method to crawl a single page"""
        # Check for duplicates first
        if self.duplicate_detector.is_duplicate(url):
            logger.info(f"Duplicate URL skipped: {url}")
            return None
        
        response = self.fetch_page(url)
        if not response:
            return None
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract information
        title = self.extract_title(soup)
        content = self.extract_content(soup)
        metadata = self.extract_metadata(soup, url)
        links = self.extract_links(soup, url)
        
        # Generate content hash
        content_hash = self.compute_content_hash(content)
        
        # Mark URL as seen
        self.duplicate_detector.mark_seen(url, content_hash)
        
        # Extract keywords
        keywords = self.extract_keywords(content)
        
        # Compute statistics
        stats = {
            'word_count': len(content.split()),
            'content_length': len(content),
            'title_length': len(title),
            'num_links': len(links),
            'num_keywords': len(keywords)
        }
        
        return {
            'url': url,
            'title': title,
            'content': content,
            'content_hash': content_hash,
            'metadata': metadata,
            'links': links,
            'keywords': keywords,
            'stats': stats,
            'crawl_date': time.time()
        }
    
    def batch_crawl(self, urls, max_workers=5):
        """Crawl multiple URLs concurrently"""
        import concurrent.futures
        
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {executor.submit(self.crawl_page, url): url for url in urls}
            
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                        logger.info(f"Successfully crawled: {url}")
                    else:
                        logger.warning(f"Failed to crawl: {url}")
                except Exception as e:
                    logger.error(f"Error crawling {url}: {e}")
        
        return results


class ContentExtractor:
    """Specialized content extractors for different types of pages"""
    
    @staticmethod
    def extract_article(soup, url):
        """Extract article content specifically"""
        article_data = {
            'type': 'article',
            'title': None,
            'author': None,
            'publish_date': None,
            'content': None
        }
        
        # Title
        title_elem = soup.select_one('h1, .title, .article-title')
        if title_elem:
            article_data['title'] = title_elem.get_text(strip=True)
        
        # Author
        author_elem = soup.select_one('.author, .byline, [rel="author"]')
        if author_elem:
            article_data['author'] = author_elem.get_text(strip=True)
        
        # Publish date
        date_elem = soup.select_one('.date, .publish-date, [datetime], time')
        if date_elem:
            article_data['publish_date'] = date_elem.get('datetime') or date_elem.get_text(strip=True)
        
        # Content
        content_elem = soup.select_one('article, .content, .article-content')
        if content_elem:
            article_data['content'] = content_elem.get_text(strip=True)
        
        return article_data
    
    @staticmethod
    def extract_product(soup, url):
        """Extract product information from e-commerce pages"""
        product_data = {
            'type': 'product',
            'name': None,
            'price': None,
            'description': None,
            'availability': None
        }
        
        # Product name
        name_elem = soup.select_one('.product-name, h1, .title')
        if name_elem:
            product_data['name'] = name_elem.get_text(strip=True)
        
        # Price
        price_elem = soup.select_one('.price, .product-price, [itemprop="price"]')
        if price_elem:
            product_data['price'] = price_elem.get_text(strip=True)
        
        # Description
        desc_elem = soup.select_one('.description, .product-description')
        if desc_elem:
            product_data['description'] = desc_elem.get_text(strip=True)
        
        # Availability
        avail_elem = soup.select_one('.availability, .stock')
        if avail_elem:
            product_data['availability'] = avail_elem.get_text(strip=True)
        
        return product_data
