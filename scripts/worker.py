import redis
import time
from db import *
from utils import *

r = redis.Redis(host='localhost', port=6379, db=0)


def process(pid, cursor, conn):
    print(f"[DEBUG] Starting process for {pid}")
    
    try:
        paper = parse_abstract(pid, r)
        print(f"[DEBUG] Parsed paper: {paper.get('paper_id', 'N/A')}")
        print(f"[DEBUG] Title: {paper.get('title', 'N/A')[:50]}...")
        print(f"[DEBUG] Authors count: {len(paper.get('authors', []))}")
        print(f"[DEBUG] Abstract length: {len(paper.get('abstract', ''))}")
    except Exception as e:
        print(f"[DEBUG] Failed to parse paper {pid}: {e}")
        raise

    try:
        paper_id = insert_paper(cursor, paper)
        print(f"[DEBUG] Inserted paper with ID: {paper_id}")
    except Exception as e:
        print(f"[DEBUG] Failed to insert paper {pid}: {e}")
        raise

    # Authors
    try:
        author_count = 0
        for a in paper["authors"]:
            aid = insert_author(cursor, a)
            link_paper_author(cursor, paper_id, aid)
            author_count += 1
        print(f"[DEBUG] Linked {author_count} authors")
    except Exception as e:
        print(f"[DEBUG] Failed to link authors: {e}")
        raise

    # Subjects
    try:
        subject_count = 0
        for s in paper["subjects"]:
            sid = insert_subject(cursor, s)
            link_paper_subject(cursor, paper_id, sid)
            subject_count += 1
        print(f"[DEBUG] Linked {subject_count} subjects")
    except Exception as e:
        print(f"[DEBUG] Failed to link subjects: {e}")
        raise

    # Keywords
    try:
        kws = extract_keywords(paper["abstract"])
        keyword_count = 0
        for k in kws:
            kid = insert_keyword(cursor, k)
            link_paper_keyword(cursor, paper_id, kid)
            keyword_count += 1
        print(f"[DEBUG] Linked {keyword_count} keywords")
    except Exception as e:
        print(f"[DEBUG] Failed to link keywords: {e}")
        raise

    # Stats
    try:
        stats = compute_stats(paper)
        insert_stats(cursor, paper_id, stats)
        print(f"[DEBUG] Inserted stats")
    except Exception as e:
        print(f"[DEBUG] Failed to insert stats: {e}")
        raise

    try:
        conn.commit()
        print(f"[DEBUG] Transaction committed successfully for {pid}")
    except Exception as e:
        print(f"[DEBUG] Failed to commit transaction: {e}")
        conn.rollback()
        raise
    
    print(f"[DEBUG] Process completed successfully for {pid}")


def main():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        print(f"[DEBUG] Database connection established successfully")
        print(f"[DEBUG] Connected to database: {conn.database}")
    except Exception as e:
        print(f"[DEBUG] Failed to establish database connection: {e}")
        return

    print("Worker started...")
    print(f"[DEBUG] Worker ready to process papers from Redis queue")

    while True:
        try:
            item = r.zpopmin("paper_queue")

            if not item:
                time.sleep(1)
                continue
            
            pid = item[0][0].decode()
            print(f"[DEBUG] Retrieved paper from queue: {pid}")

            try:
                print(f"[DEBUG] Starting processing for: {pid}")
                process(pid, cursor, conn)
                print(f"[DEBUG] Completed processing for: {pid}")

            except Exception as e:
                print(f"[ERROR] Processing failed for {pid}: {e}")
                print(f"[DEBUG] Rolling back transaction for: {pid}")
                conn.rollback()

        except Exception as e:
            print(f"[ERROR] Worker loop error: {e}")
            time.sleep(5)  # Wait before retrying


if __name__ == "__main__":
    main()