import mysql.connector


def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="crawler_user",
        password="crawler_pass",
        database="arxiv_db",
        autocommit=False
    )


# ------------------ PAPERS ------------------

def insert_paper(cursor, paper):
    query = """
    INSERT INTO papers (paper_id, title, abstract, primary_subject, submission_info, url)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)
    """

    try:
        print(f"[DB_DEBUG] Inserting paper: {paper.get('paper_id', 'N/A')}")
        print(f"[DB_DEBUG] Title length: {len(paper.get('title', ''))}")
        print(f"[DB_DEBUG] Abstract length: {len(paper.get('abstract', ''))}")
        
        cursor.execute(query, (
            paper["paper_id"],
            paper["title"],
            paper["abstract"],
            paper["primary_subject"],
            paper["submission_info"],
            paper["url"]
        ))
        
        paper_id = cursor.lastrowid
        print(f"[DB_DEBUG] Insert executed, returned paper_id: {paper_id}")
        
        # Check if this was an insert or update
        cursor.execute("SELECT ROW_COUNT()")
        row_count = cursor.fetchone()[0]
        print(f"[DB_DEBUG] Row count: {row_count}")
        
        return paper_id
        
    except Exception as e:
        print(f"[DB_DEBUG] Insert failed: {e}")
        print(f"[DB_DEBUG] Query: {query}")
        print(f"[DB_DEBUG] Data: paper_id={paper.get('paper_id', 'N/A')}, title={paper.get('title', 'N/A')[:30]}...")
        raise


# ------------------ AUTHORS ------------------

def insert_author(cursor, name):
    query = """
    INSERT INTO authors (name)
    VALUES (%s)
    ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)
    """

    cursor.execute(query, (name,))
    return cursor.lastrowid


def link_paper_author(cursor, paper_id, author_id):
    query = """
    INSERT IGNORE INTO paper_authors (paper_id, author_id)
    VALUES (%s, %s)
    """

    cursor.execute(query, (paper_id, author_id))


# ------------------ SUBJECTS ------------------

def insert_subject(cursor, name):
    query = """
    INSERT INTO subjects (name)
    VALUES (%s)
    ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)
    """

    cursor.execute(query, (name,))
    return cursor.lastrowid


def link_paper_subject(cursor, paper_id, subject_id):
    query = """
    INSERT IGNORE INTO paper_subjects (paper_id, subject_id)
    VALUES (%s, %s)
    """

    cursor.execute(query, (paper_id, subject_id))


# ------------------ KEYWORDS ------------------

def insert_keyword(cursor, word):
    query = """
    INSERT INTO keywords (word)
    VALUES (%s)
    ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)
    """

    cursor.execute(query, (word,))
    return cursor.lastrowid


def link_paper_keyword(cursor, paper_id, keyword_id):
    query = """
    INSERT IGNORE INTO paper_keywords (paper_id, keyword_id)
    VALUES (%s, %s)
    """

    cursor.execute(query, (paper_id, keyword_id))


# ------------------ STATS ------------------

def insert_stats(cursor, paper_id, stats):
    query = """
    INSERT INTO paper_stats (paper_id, word_count, abstract_length, title_length, num_authors)
    VALUES (%s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE paper_id=paper_id
    """

    cursor.execute(query, (
        paper_id,
        stats["word_count"],
        stats["abstract_length"],
        stats["title_length"],
        stats["num_authors"]
    ))