# -*- coding: utf-8 -*-
import os
import bibtexparser # type: ignore
import psycopg2 # type: ignore
from psycopg2 import sql # type: ignore
import pandas as pd # type: ignore
from dotenv import load_dotenv # type: ignore

# Load environment variables from the .env file
load_dotenv()

db_config = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT')
}

# Connecting to PostgreSQL to create the database if necessary
try:
    conn = psycopg2.connect(dbname='postgres', user=db_config['user'], password=db_config['password'], host=db_config['host'], port=db_config['port'])
    conn.autocommit = True
    cursor = conn.cursor()
    
    cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (db_config['dbname'],))
    exists = cursor.fetchone()
    if not exists:
        cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_config['dbname'])))
        print(f"Database '{db_config['dbname']}' created successfully.")
    else:
        print(f"Database '{db_config['dbname']}' exists.")
        
        conn.close()
        conn = psycopg2.connect(**db_config)
        conn.autocommit = True
        cursor = conn.cursor()

        # Check and drop tables if they exist
        cursor.execute("DROP TABLE IF EXISTS article_keywords CASCADE")
        cursor.execute("DROP TABLE IF EXISTS keywords CASCADE")
        cursor.execute("DROP TABLE IF EXISTS articles CASCADE")
        cursor.execute("DROP TABLE IF EXISTS article_authors CASCADE")
        cursor.execute("DROP TABLE IF EXISTS authors CASCADE")
        cursor.execute("DROP TABLE IF EXISTS journals CASCADE")
        conn.commit()
        print("Existing tables were successfully dropped.")

    cursor.close()
    conn.close()
except Exception as e:
    print(f"Tables created error: {e}")

# Create tables and relationships
try:
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()

    cursor.execute('''
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'article_status') THEN
            CREATE TYPE article_status AS ENUM ('Accepted', 'Rejected', 'Unclassified', 'Duplicated');
        END IF;
    END $$;
    ''')

    cursor.execute('''
    CREATE TABLE journals (
        id SERIAL PRIMARY KEY,
        name TEXT UNIQUE
    )
    ''')

    cursor.execute('''
    CREATE TABLE authors (
        id SERIAL PRIMARY KEY,
        name TEXT UNIQUE
    )
    ''')

    cursor.execute('''
    CREATE TABLE articles (
        id SERIAL PRIMARY KEY,
        bibtex_id TEXT,
        journal_id INTEGER REFERENCES journals(id),
        title TEXT,
        year INTEGER,
        volume TEXT,
        number TEXT,
        pages TEXT,
        abstract TEXT,
        keywords TEXT,
        doi TEXT,
        issn TEXT,
        month TEXT,
        status article_status DEFAULT 'Unclassified',
        publisher TEXT,
        eissn TEXT,
        isbn TEXT,
        language TEXT,
        conference TEXT,
        address TEXT,
        pubmed_id TEXT,
        document_type TEXT,
        degree TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE article_authors (
        article_id INTEGER REFERENCES articles(id),
        author_id INTEGER REFERENCES authors(id),
        PRIMARY KEY (article_id, author_id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE keywords (
        id SERIAL PRIMARY KEY,
        keyword TEXT UNIQUE
    )
    ''')

    cursor.execute('''
    CREATE TABLE article_keywords (
        article_id INTEGER REFERENCES articles(id),
        keyword_id INTEGER REFERENCES keywords(id),
        PRIMARY KEY (article_id, keyword_id)
    )
    ''')

    conn.commit()
    print("Tables created successfully.")
except Exception as e:
    print(f"Error connecting to the PostgreSQL database: {e}")
finally:
    if conn:
        conn.close()

# Function to read and parse BibTeX files
def parse_bibtex_files(directory):
    articles = []
    for filename in os.listdir(directory):
        if filename.endswith(".bib"):
            print(f"Importing file: {filename}")
            with open(os.path.join(directory, filename), 'r', encoding='utf-8') as bibtex_file:
                bib_database = bibtexparser.load(bibtex_file)
                for entry in bib_database.entries:
                    articles.append(entry)
    return articles

def process_keywords(keyword_string):
    delimiters = [';', ',', '--', '---']
    for delimiter in delimiters:
        keyword_string = keyword_string.replace(delimiter, ';')
    
    keywords = [kw.strip().lower() for kw in keyword_string.split(';') if kw.strip()]
    return set(keywords)

# Function to insert and link articles, authors, and journals
# Insert articles into the database
def insert_articles_into_db(articles):
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()
    for entry in articles:
        # Insert journal if it does not exist
        journal_name = entry.get('journal', '').strip()
        if journal_name:
            cursor.execute('''
                INSERT INTO journals (name)
                VALUES (%s)
                ON CONFLICT (name) DO NOTHING
            ''', (journal_name,))
            conn.commit()

            # Retrieve the journal ID
            cursor.execute('SELECT id FROM journals WHERE name = %s', (journal_name,))
            journal_id_result = cursor.fetchone()
            journal_id = journal_id_result[0] if journal_id_result else None
        else:
            journal_id = None

        # Insert article
        cursor.execute('SELECT id FROM articles WHERE doi = %s', (entry.get('doi', ''),))
        existing_article = cursor.fetchone()
        status = 'Duplicated' if existing_article else 'Unclassified'

        cursor.execute('''
            INSERT INTO articles (bibtex_id, journal_id, title, year, volume, number, pages, abstract, keywords, doi, issn, 
                                month, status, publisher, eissn, isbn, language, conference, address, pubmed_id, document_type, degree)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            entry.get('ID', ''),
            journal_id,
            entry.get('title', ''),
            int(entry.get('year', 0)) if entry.get('year') and entry.get('year').isdigit() else None,
            entry.get('volume', ''),
            entry.get('number', ''),
            entry.get('pages', ''),
            entry.get('abstract', ''),
            entry.get('keywords', ''),
            entry.get('doi', ''),
            entry.get('issn', ''),
            entry.get('month', ''),
            status,
            entry.get('publisher', ''),
            entry.get('eissn', ''),
            entry.get('isbn', ''),
            entry.get('language', ''),
            entry.get('conference', ''),
            entry.get('address', ''),
            entry.get('pubmed_id', ''),
            entry.get('document_type', ''),
            entry.get('degree', '')
        ))
        conn.commit()

        # Link authors
        if 'author' in entry and entry['author']:
            authors = [author.strip() for author in entry['author'].split(' and ')]
            for author in authors:
                cursor.execute('''
                    INSERT INTO authors (name)
                    VALUES (%s)
                    ON CONFLICT (name) DO NOTHING
                ''', (author,))
                conn.commit()

                cursor.execute('SELECT id FROM authors WHERE name = %s', (author,))
                author_id_result = cursor.fetchone()
                author_id = author_id_result[0] if author_id_result else None

                cursor.execute('SELECT id FROM articles WHERE bibtex_id = %s', (entry.get('ID', ''),))
                article_id_result = cursor.fetchone()
                article_id = article_id_result[0] if article_id_result else None

                if article_id and author_id:
                    cursor.execute('''
                        INSERT INTO article_authors (article_id, author_id)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING
                    ''', (article_id, author_id))
                    conn.commit()

        # Link keywords with the inserted article
        if 'keywords' in entry and entry['keywords']:
            keywords = process_keywords(entry['keywords'])
            for keyword in keywords:
                cursor.execute('''
                    INSERT INTO keywords (keyword)
                    VALUES (%s)
                    ON CONFLICT (keyword) DO NOTHING
                ''', (keyword,))
                conn.commit()

                cursor.execute('SELECT id FROM keywords WHERE keyword = %s', (keyword,))
                keyword_id_result = cursor.fetchone()
                keyword_id = keyword_id_result[0] if keyword_id_result else None

                cursor.execute('SELECT id FROM articles WHERE bibtex_id = %s', (entry.get('ID', ''),))
                article_id_result = cursor.fetchone()
                article_id = article_id_result[0] if article_id_result else None

                if article_id and keyword_id:
                    cursor.execute('''
                        INSERT INTO article_keywords (article_id, keyword_id)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING
                    ''', (article_id, keyword_id))
                    conn.commit()

    cursor.close()
    conn.close()
    print("Articles successfully inserted and linked with authors and journals.")

def list_data_count():
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()

    # Total records in the articles table
    cursor.execute("SELECT COUNT(*) FROM articles")
    total_count = cursor.fetchone()[0]
    print(f"\nTotal records: {total_count}")

    # Total articles by status
    cursor.execute('''
    SELECT status, COUNT(*)
    FROM articles
    GROUP BY status
    ORDER BY COUNT(*) DESC;
    ''')
    status_counts = cursor.fetchall()

    print("\nTotal articles by status:")
    print(f"{'Status':<20} {'Total Articles':<20}")
    print("-" * 40)
    for status, count in status_counts:
        print(f"{status:<20} {count:<20}")

    # Total listing of document types and their count
    cursor.execute('''
    SELECT document_type, COUNT(*)
    FROM articles
    WHERE status <> 'Duplicated'
    GROUP BY document_type
    ORDER BY COUNT(*) DESC;
    ''')
    document_type_counts = cursor.fetchall()

    print("\nDocument type and total articles (Excluding Duplicates):")
    print(f"{'Document Type':<30} {'Total Articles':<20}")
    print("-" * 50)
    for doc_type, count in document_type_counts:
        print(f"{doc_type:<30} {count:<20}")              

    # # List journals and total articles
    # cursor.execute('''
    # SELECT j.name, COUNT(a.id)
    # FROM journals j
    # JOIN articles a ON j.id = a.journal_id
    # GROUP BY j.name
    # ORDER BY COUNT(a.id) DESC;
    # ''')
    # journal_counts = cursor.fetchall()

    # print("\nJournals and total articles:")
    # print(f"{'Journal':<30} {'Total Articles':<20}")
    # print("-" * 50)
    # for journal, count in journal_counts:
    #     print(f"{journal:<30} {count:<20}")

    # # List authors and total associated articles
    # cursor.execute('''
    # SELECT au.name, COUNT(aa.article_id)
    # FROM authors au
    # JOIN article_authors aa ON au.id = aa.author_id
    # GROUP BY au.name
    # ORDER BY COUNT(aa.article_id) DESC;
    # ''')
    # author_counts = cursor.fetchall()

    # print("\nAuthors and total articles:")
    # print(f"{'Author':<30} {'Total Articles':<20}")
    # print("-" * 50)
    # for author, count in author_counts:
    #     print(f"{author:<30} {count:<20}")

    # # List publishers and total articles
    # cursor.execute('''
    # SELECT publisher, COUNT(*)
    # FROM articles
    # WHERE publisher IS NOT NULL AND publisher <> ''
    # GROUP BY publisher
    # ORDER BY COUNT(*) DESC;
    # ''')
    # publisher_counts = cursor.fetchall()

    # print("\nPublishers and total articles:")
    # print(f"{'Publisher':<30} {'Total Articles':<20}")
    # print("-" * 50)
    # for publisher, count in publisher_counts:
    #     print(f"{publisher:<30} {count:<20}")

    # # List keywords and total associated articles, excluding duplicates
    # cursor.execute('''
    # SELECT k.keyword, COUNT(ak.article_id)
    # FROM keywords k
    # JOIN article_keywords ak ON k.id = ak.keyword_id
    # JOIN articles a ON ak.article_id = a.id
    # WHERE a.status <> 'Duplicated'
    # GROUP BY k.keyword
    # ORDER BY COUNT(ak.article_id) ASC;
    # ''')
    # keyword_counts = cursor.fetchall()

    # print("\nKeywords and total articles (excluding duplicates):")
    # print(f"{'Keyword':<30} {'Total Articles':<20}")
    # print("-" * 50)
    # for keyword, count in keyword_counts:
    #     print(f"{keyword:<30} {count:<20}")  

    cursor.close()
    conn.close()

def export_articles_to_excel():
    """Exporta todos os dados da tabela articles para um arquivo Excel."""
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM articles ORDER BY status')
    articles = cursor.fetchall()

    column_names = [desc[0] for desc in cursor.description]
    df = pd.DataFrame(articles, columns=column_names)

    output_file = "articles_data.xlsx"
    df.to_excel(output_file, index=False, engine="openpyxl")

    print(f"\nExcel file generated: {output_file}")

    cursor.close()
    conn.close()


directory_path = os.getcwd()

articles_list = parse_bibtex_files(directory_path)
insert_articles_into_db(articles_list)
list_data_count()
export_articles_to_excel()
