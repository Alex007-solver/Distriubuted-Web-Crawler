#!/usr/bin/env python3
"""
Debug script to identify database insertion issues
"""

import sys
import mysql.connector
from pathlib import Path

# Add scripts directory to path
sys.path.append(str(Path(__file__).parent / "scripts"))

from db import get_connection, insert_paper

def test_database_connection():
    """Test basic database connection"""
    print("=== Testing Database Connection ===")
    try:
        conn = get_connection()
        print(f"✓ Connected to MySQL successfully")
        print(f"  Connection info: {conn.get_info()}")
        return conn
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return None

def test_database_schema(conn):
    """Test if tables exist"""
    print("\n=== Testing Database Schema ===")
    try:
        cursor = conn.cursor()
        
        # Check if papers table exists
        cursor.execute("SHOW TABLES LIKE 'papers'")
        result = cursor.fetchone()
        if result:
            print(f"✓ papers table exists")
        else:
            print(f"✗ papers table NOT found")
            return False
        
        # Check papers table structure
        cursor.execute("DESCRIBE papers")
        columns = cursor.fetchall()
        print(f"  papers table has {len(columns)} columns:")
        for col in columns:
            print(f"    - {col[0]} ({col[1]})")
        
        return True
    except Exception as e:
        print(f"✗ Schema check failed: {e}")
        return False

def test_simple_insert(conn):
    """Test a simple insert operation"""
    print("\n=== Testing Simple Insert ===")
    try:
        cursor = conn.cursor()
        
        # Test paper data
        test_paper = {
            "paper_id": "test1234",
            "title": "Test Paper for Debugging",
            "abstract": "This is a test abstract to verify database insertion works properly.",
            "primary_subject": "Computer Science",
            "submission_info": "Test submission",
            "url": "https://arxiv.org/abs/test1234"
        }
        
        print(f"  Attempting to insert test paper: {test_paper['paper_id']}")
        paper_id = insert_paper(cursor, test_paper)
        print(f"  Insert returned paper_id: {paper_id}")
        
        # Commit the transaction
        conn.commit()
        print(f"  Transaction committed")
        
        # Verify the insert
        cursor.execute("SELECT id, paper_id, title FROM papers WHERE paper_id = %s", (test_paper['paper_id'],))
        result = cursor.fetchone()
        if result:
            print(f"✓ Insert verified: id={result[0]}, paper_id={result[1]}, title={result[2]}")
            return True
        else:
            print(f"✗ Insert not found in database")
            return False
            
    except Exception as e:
        print(f"✗ Simple insert failed: {e}")
        conn.rollback()
        return False

def test_worker_flow():
    """Test the complete worker flow with one paper"""
    print("\n=== Testing Worker Flow ===")
    try:
        from utils import parse_abstract
        import redis
        
        # Connect to Redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✓ Redis connection successful")
        
        # Test parsing a known arXiv paper
        test_pid = "2401.00001"  # This should exist
        print(f"  Testing parsing of {test_pid}")
        
        paper = parse_abstract(test_pid, r)
        if paper:
            print(f"✓ Paper parsed successfully")
            print(f"  Title: {paper.get('title', 'N/A')[:50]}...")
            print(f"  Authors: {len(paper.get('authors', []))}")
            print(f"  Abstract length: {len(paper.get('abstract', ''))}")
            
            # Test database insert
            conn = get_connection()
            cursor = conn.cursor()
            
            paper_id = insert_paper(cursor, paper)
            print(f"  Database insert returned paper_id: {paper_id}")
            
            conn.commit()
            
            # Verify
            cursor.execute("SELECT id, title FROM papers WHERE paper_id = %s", (paper['paper_id'],))
            result = cursor.fetchone()
            if result:
                print(f"✓ Worker flow successful: id={result[0]}, title={result[1][:50]}...")
                return True
            else:
                print(f"✗ Paper not found after insert")
                return False
        else:
            print(f"✗ Failed to parse paper {test_pid}")
            return False
            
    except Exception as e:
        print(f"✗ Worker flow failed: {e}")
        return False

def check_current_data():
    """Check current data in papers table"""
    print("\n=== Current Database State ===")
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Count papers
        cursor.execute("SELECT COUNT(*) FROM papers")
        count = cursor.fetchone()[0]
        print(f"Total papers in database: {count}")
        
        if count > 0:
            # Show recent papers
            cursor.execute("SELECT id, paper_id, title, url FROM papers ORDER BY id DESC LIMIT 5")
            papers = cursor.fetchall()
            print(f"Recent papers:")
            for paper in papers:
                print(f"  id={paper[0]}, paper_id={paper[1]}, title={paper[2][:50]}...")
        
        return count
    except Exception as e:
        print(f"✗ Failed to check current data: {e}")
        return 0

def main():
    print("Database Debugging Script")
    print("=" * 50)
    
    # Test database connection
    conn = test_database_connection()
    if not conn:
        return
    
    # Check current state
    current_count = check_current_data()
    
    # Test schema
    if not test_database_schema(conn):
        return
    
    # Test simple insert
    if test_simple_insert(conn):
        print("\n✓ Simple insert test passed")
    else:
        print("\n✗ Simple insert test failed")
        return
    
    # Test worker flow
    if test_worker_flow():
        print("\n✓ Worker flow test passed")
    else:
        print("\n✗ Worker flow test failed")
    
    # Final check
    final_count = check_current_data()
    if final_count > current_count:
        print(f"\n✓ SUCCESS: Database insertion is working! Papers increased from {current_count} to {final_count}")
    else:
        print(f"\n✗ ISSUE: No new papers added. Count remains {current_count}")
    
    conn.close()

if __name__ == "__main__":
    main()
