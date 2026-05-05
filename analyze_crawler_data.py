#!/usr/bin/env python3
"""
Data Analysis & Visualization for Distributed Web Crawler
Uses pandas, matplotlib, and networkx to analyze crawler data
"""

import sys
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
from sqlalchemy import create_engine
from collections import Counter
import seaborn as sns
from pathlib import Path
import argparse

# Add scripts directory to path
sys.path.append(str(Path(__file__).parent / "scripts"))

from models import get_db_session, Paper, PaperStats, DiscoveredLink, Keyword, PaperKeyword

class CrawlerDataAnalyzer:
    """Analyze and visualize crawler data"""
    
    def __init__(self, database_url="mysql+pymysql://crawler_user:crawler_pass@localhost/crawler_db"):
        self.engine = create_engine(database_url)
        self.setup_plotting()
    
    def setup_plotting(self):
        """Setup matplotlib and seaborn styling"""
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        plt.rcParams['figure.figsize'] = (12, 8)
        plt.rcParams['font.size'] = 10
    
    def load_data(self):
        """Load data from database into pandas DataFrames"""
        print("Loading data from database...")
        
        # Load papers with stats
        papers_query = """
        SELECT p.*, ps.word_count, ps.content_length, ps.title_length, 
               ps.num_keywords, ps.num_links
        FROM papers p
        LEFT JOIN paper_stats ps ON p.id = ps.paper_id
        WHERE p.status = 'completed'
        """
        
        self.papers_df = pd.read_sql(papers_query, self.engine)
        print(f"Loaded {len(self.papers_df)} papers")
        
        # Load discovered links
        links_query = "SELECT * FROM discovered_links"
        self.links_df = pd.read_sql(links_query, self.engine)
        print(f"Loaded {len(self.links_df)} discovered links")
        
        # Load keywords
        keywords_query = """
        SELECT pk.paper_id, k.word
        FROM paper_keywords pk
        JOIN keywords k ON pk.keyword_id = k.id
        """
        self.keywords_df = pd.read_sql(keywords_query, self.engine)
        print(f"Loaded {len(self.keywords_df)} keyword associations")
        
        return self.papers_df, self.links_df, self.keywords_df
    
    def analyze_domains(self):
        """Analyze most common domains crawled"""
        if self.papers_df.empty:
            print("No papers data available for domain analysis")
            return
        
        # Extract domain from URL
        self.papers_df['domain'] = self.papers_df['url'].str.extract(r'://([^/]+)')
        
        # Count domains
        domain_counts = self.papers_df['domain'].value_counts().head(10)
        
        print("\nTop 10 Most Crawled Domains:")
        print(domain_counts)
        
        # Create bar chart
        plt.figure(figsize=(12, 6))
        domain_counts.plot(kind='bar')
        plt.title('Top 10 Most Crawled Domains')
        plt.xlabel('Domain')
        plt.ylabel('Number of Pages Crawled')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig('domain_analysis.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        return domain_counts
    
    def analyze_content_stats(self):
        """Analyze content statistics and create scatter plot"""
        if self.papers_df.empty or 'word_count' not in self.papers_df.columns:
            print("No content statistics available")
            return
        
        # Create scatter plot of word count vs number of links
        plt.figure(figsize=(12, 8))
        
        # Filter out rows with missing data
        valid_data = self.papers_df.dropna(subset=['word_count', 'num_links'])
        
        if not valid_data.empty:
            scatter = plt.scatter(
                valid_data['word_count'], 
                valid_data['num_links'],
                alpha=0.6,
                s=50,
                c=valid_data['num_keywords'],
                cmap='viridis'
            )
            plt.colorbar(scatter, label='Number of Keywords')
            plt.title('Content Analysis: Word Count vs Number of Links')
            plt.xlabel('Word Count')
            plt.ylabel('Number of Links')
            plt.grid(True, alpha=0.3)
            
            # Add trend line
            if len(valid_data) > 1:
                z = np.polyfit(valid_data['word_count'], valid_data['num_links'], 1)
                p = np.poly1d(z)
                plt.plot(valid_data['word_count'], p(valid_data['word_count']), "r--", alpha=0.8)
            
            plt.tight_layout()
            plt.savefig('content_scatter.png', dpi=300, bbox_inches='tight')
            plt.show()
        
        # Print summary statistics
        print("\nContent Statistics Summary:")
        print(valid_data[['word_count', 'content_length', 'num_keywords', 'num_links']].describe())
    
    def analyze_keywords(self):
        """Analyze most common keywords"""
        if self.keywords_df.empty:
            print("No keyword data available")
            return
        
        # Count keywords
        keyword_counts = self.keywords_df['word'].value_counts().head(20)
        
        print("\nTop 20 Most Common Keywords:")
        print(keyword_counts)
        
        # Create horizontal bar chart
        plt.figure(figsize=(12, 8))
        keyword_counts.plot(kind='barh')
        plt.title('Top 20 Most Common Keywords')
        plt.xlabel('Frequency')
        plt.ylabel('Keyword')
        plt.gca().invert_yaxis()  # Highest frequency at top
        plt.tight_layout()
        plt.savefig('keyword_analysis.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        return keyword_counts
    
    def create_network_graph(self):
        """Create network visualization of discovered links"""
        if self.links_df.empty:
            print("No link data available for network analysis")
            return
        
        print("Creating network graph...")
        
        # Create network graph
        G = nx.DiGraph()
        
        # Add edges from discovered links
        # Limit to first 1000 links for performance
        sample_links = self.links_df.head(1000)
        
        for _, row in sample_links.iterrows():
            G.add_edge(row['source_url'], row['target_url'], 
                       anchor_text=row.get('anchor_text', ''))
        
        print(f"Network created with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
        
        # Calculate network metrics
        if G.number_of_nodes() > 0:
            # Calculate centrality measures
            in_degree = dict(G.in_degree())
            out_degree = dict(G.out_degree())
            
            # Find most connected nodes
            top_in_nodes = sorted(in_degree.items(), key=lambda x: x[1], reverse=True)[:5]
            top_out_nodes = sorted(out_degree.items(), key=lambda x: x[1], reverse=True)[:5]
            
            print("\nTop 5 Nodes by In-degree (most linked to):")
            for url, degree in top_in_nodes:
                print(f"  {url[:60]}...: {degree}")
            
            print("\nTop 5 Nodes by Out-degree (most links from):")
            for url, degree in top_out_nodes:
                print(f"  {url[:60]}...: {degree}")
        
        # Create visualization
        plt.figure(figsize=(16, 12))
        
        # Use spring layout for positioning
        if G.number_of_nodes() <= 100:
            pos = nx.spring_layout(G, k=2, iterations=50)
        else:
            # For larger graphs, use a faster layout
            pos = nx.spring_layout(G, k=1, iterations=20)
        
        # Draw nodes with size based on degree
        node_sizes = [G.degree(node) * 10 for node in G.nodes()]
        nx.draw_networkx_nodes(G, pos, node_size=node_sizes, 
                              node_color='lightblue', alpha=0.7)
        
        # Draw edges
        nx.draw_networkx_edges(G, pos, alpha=0.3, width=0.5, 
                              edge_color='gray', arrows=True, 
                              arrowsize=10, arrowstyle='->')
        
        # Draw labels for important nodes only (high degree)
        high_degree_nodes = [node for node in G.nodes() if G.degree(node) > 5]
        if high_degree_nodes:
            labels = {node: node.split('/')[2] if '/' in node else node[:20] 
                     for node in high_degree_nodes}
            nx.draw_networkx_labels(G, pos, labels, font_size=8, font_weight='bold')
        
        plt.title('Crawler Network Graph\nNode size represents degree (number of connections)', 
                 fontsize=14)
        plt.axis('off')
        plt.tight_layout()
        plt.savefig('network_graph.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        return G
    
    def analyze_crawl_timeline(self):
        """Analyze crawling activity over time"""
        if 'crawl_date' not in self.papers_df.columns:
            print("No crawl date data available")
            return
        
        # Convert crawl_date to datetime if it's not already
        self.papers_df['crawl_date'] = pd.to_datetime(self.papers_df['crawl_date'])
        
        # Extract date and hour
        self.papers_df['crawl_date_only'] = self.papers_df['crawl_date'].dt.date
        self.papers_df['crawl_hour'] = self.papers_df['crawl_date'].dt.hour
        
        # Daily crawling activity
        daily_counts = self.papers_df.groupby('crawl_date_only').size()
        
        plt.figure(figsize=(14, 6))
        
        plt.subplot(1, 2, 1)
        daily_counts.plot(kind='line', marker='o')
        plt.title('Daily Crawling Activity')
        plt.xlabel('Date')
        plt.ylabel('Pages Crawled')
        plt.xticks(rotation=45)
        plt.grid(True, alpha=0.3)
        
        # Hourly crawling activity
        hourly_counts = self.papers_df.groupby('crawl_hour').size()
        
        plt.subplot(1, 2, 2)
        hourly_counts.plot(kind='bar')
        plt.title('Hourly Crawling Activity')
        plt.xlabel('Hour of Day')
        plt.ylabel('Pages Crawled')
        plt.xticks(range(0, 24, 2))
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('crawl_timeline.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"\nCrawling Period: {daily_counts.index.min()} to {daily_counts.index.max()}")
        print(f"Total Days: {len(daily_counts)}")
        print(f"Peak Crawling Day: {daily_counts.idxmax()} ({daily_counts.max()} pages)")
        print(f"Peak Crawling Hour: {hourly_counts.idxmax()} ({hourly_counts.max()} pages)")
    
    def generate_summary_report(self):
        """Generate comprehensive summary report"""
        print("\n" + "="*60)
        print("CRAWLER DATA ANALYSIS SUMMARY REPORT")
        print("="*60)
        
        if not self.papers_df.empty:
            print(f"\n📊 OVERVIEW:")
            print(f"  Total Papers Crawled: {len(self.papers_df)}")
            print(f"  Total Discovered Links: {len(self.links_df)}")
            print(f"  Total Keyword Associations: {len(self.keywords_df)}")
            
            if 'domain' in self.papers_df.columns:
                print(f"  Unique Domains: {self.papers_df['domain'].nunique()}")
            
            if 'word_count' in self.papers_df.columns:
                avg_words = self.papers_df['word_count'].mean()
                print(f"  Average Word Count: {avg_words:.1f}")
            
            print(f"\n📈 GENERATED VISUALIZATIONS:")
            print("  1. domain_analysis.png - Top crawled domains")
            print("  2. content_scatter.png - Content analysis scatter plot")
            print("  3. keyword_analysis.png - Most common keywords")
            print("  4. network_graph.png - Link network visualization")
            print("  5. crawl_timeline.png - Crawling activity timeline")
        
        print("\n✅ Analysis complete! Check the generated PNG files.")


def main():
    """Main function to run data analysis"""
    parser = argparse.ArgumentParser(description='Analyze crawler data')
    parser.add_argument('--db-url', help='Database URL', 
                       default='mysql+pymysql://crawler_user:crawler_pass@localhost/crawler_db')
    parser.add_argument('--output-dir', help='Output directory for plots', 
                       default='.')
    
    args = parser.parse_args()
    
    try:
        # Import numpy for trend line calculation
        import numpy as np
        
        # Create analyzer
        analyzer = CrawlerDataAnalyzer(args.db_url)
        
        # Load data
        analyzer.load_data()
        
        # Run analyses
        print("\n🔍 Running domain analysis...")
        analyzer.analyze_domains()
        
        print("\n📊 Running content statistics analysis...")
        analyzer.analyze_content_stats()
        
        print("\n🏷️ Running keyword analysis...")
        analyzer.analyze_keywords()
        
        print("\n🕸️ Creating network visualization...")
        analyzer.create_network_graph()
        
        print("\n📅 Analyzing crawl timeline...")
        analyzer.analyze_crawl_timeline()
        
        # Generate summary
        analyzer.generate_summary_report()
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
