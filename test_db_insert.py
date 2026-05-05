#!/usr/bin/env python3
"""
Simple test to verify database insertion works
"""

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.append(str(Path(__file__).parent / "scripts"))

def test_database_insert():
    """Test database insertion with minimal dependencies"""
    print("=== Testing Database Insert ===")
    
    try:
        from db import get_connection, insert_paper
        
        # Test connection
        conn = get_connection()
        cursor = conn.cursor()
        print("✓ Database connection successful")
        
        # Test simple insert
        test_paper = {
            "paper_id": "TEST_DEBUG_001",
            "title": "Debug Test Paper",
            "abstract": "This is a test paper to verify database insertion works.",
            "primary_subject": "Computer Science",
            "submission_info": "Test submission",
            "url": "https://arxiv.org/abs/TEST_DEBUG_001"
        }
        
        print(f"Attempting to insert test paper: {test_paper['paper_id']}")
        
        paper_id = insert_paper(cursor, test_paper)
        print(f"Insert returned paper_id: {paper_id}")
        
        # Commit
        conn.commit()
        print("Transaction committed")
        
        # Verify
        cursor.execute("SELECT id, paper_id, title FROM papers WHERE paper_id = %s", (test_paper['paper_id'],))
        result = cursor.fetchone()
        
        if result:
            print(f"✓ SUCCESS: Paper found in database - id={result[0]}, paper_id={result[1]}, title={result[2]}")
            return True
        else:
            print("✗ FAILURE: Paper not found in database after insert")
            return False
            
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return False
    finally:
        try:
            conn.close()
        except:
            pass

def check_current_papers():
    """Check current papers in database"""
    print("\n=== Current Papers Count ===")
    
    try:
        from db import get_connection
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM papers")
        count = cursor.fetchone()[0]
        print(f"Total papers: {count}")
        
        if count > 0:
            cursor.execute("SELECT id, paper_id, title FROM papers ORDER BY id DESC LIMIT 3")
            papers = cursor.fetchall()
            print("Recent papers:")
            for paper in papers:
                print(f"  id={paper[0]}, paper_id={paper[1]}, title={paper[2][:50]}...")
        
        conn.close()
        return count
        
    except Exception as e:
        print(f"Error checking papers: {e}")
        return 0

if __name__ == "__main__":
    # Check current state
    initial_count = check_current_papers()
    
    # Test insert
    if test_database_insert():
        # Check final state
        final_count = check_current_papers()
        
        if final_count > initial_count:
            print(f"\n✓ SUCCESS: Database insertion working! Count increased from {initial_count} to {final_count}")
        else:
            print(f"\n✗ ISSUE: Count unchanged ({initial_count} -> {final_count})")
    else:
        print(f"\n✗ FAILURE: Database insert test failed")
