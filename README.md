# BibTeX Importer

## Description
This Python script processes multiple `.bib` files, extracts metadata from them, and imports the data into a **PostgreSQL database**. Additionally, it generates an **Excel file** containing all imported articles. The script ensures:

- **Automatic database creation** if it does not exist.
- **Table structure initialization** with relationships between articles, authors, journals, and keywords.
- **Duplicate article detection**, marking them with the status `Duplicated`.
- **Comprehensive metadata storage**, including **title, authors, journal, volume, issue, pages, DOI, ISSN, eISSN, ISBN, language, conference, publisher, address, PubMed ID, document type, and degree**.
- **Exporting all data to an Excel file (`articles_data.xlsx`)** for easy access and analysis.

---

## Requirements

### 1. Install Python Dependencies
This script requires Python **3.7 or higher** and the following libraries:
```bash
pip install psycopg2 dotenv pandas bibtexparser openpyxl
```

### 2. Configure the PostgreSQL Database
Ensure that **PostgreSQL** is installed and running. The script will automatically create the required database and tables.

### 3. Create a `.env` File
The database connection credentials should be stored in a `.env` file in the same directory as the script.

Example `.env` file:
```
DB_NAME=articles_db
DB_USER=postgres
DB_PASSWORD=yourpassword
DB_HOST=localhost
DB_PORT=5432
```

---

## How to Use

### 1. Place BibTeX Files
Ensure that all **`.bib`** files to be processed are in the **same directory** as the script.

### 2. Run the Script
Execute the script using:
```bash
python import_bibtex.py
```

### 3. Process Flow
- The script reads all `.bib` files in the directory.
- Articles are inserted into the **PostgreSQL database**.
- Authors, journals, and keywords are linked correctly.
- Duplicate articles are marked as `Duplicated`.
- A final **Excel file** (`articles_data.xlsx`) is generated.

---

## Database Structure
The script automatically creates and manages the following tables:

### **`articles` Table**
| Column       | Type         | Description |
|-------------|-------------|-------------|
| id          | SERIAL PRIMARY KEY | Unique article identifier |
| bibtex_id   | TEXT        | ID from the BibTeX file |
| journal_id  | INTEGER     | Foreign key to `journals` |
| title       | TEXT        | Article title |
| year        | INTEGER     | Publication year |
| volume      | TEXT        | Journal volume |
| number      | TEXT        | Journal issue |
| pages       | TEXT        | Page range |
| abstract    | TEXT        | Article abstract |
| keywords    | TEXT        | Keywords associated with the article |
| doi         | TEXT        | Digital Object Identifier (DOI) |
| issn        | TEXT        | ISSN of the journal |
| eissn       | TEXT        | Electronic ISSN |
| isbn        | TEXT        | ISBN for books |
| language    | TEXT        | Language of the article |
| conference  | TEXT        | Conference name (if applicable) |
| publisher   | TEXT        | Publisher name |
| address     | TEXT        | Institution or conference address |
| pubmed_id   | TEXT        | PubMed ID |
| document_type | TEXT      | Type of document (e.g., article, thesis) |
| degree      | TEXT        | Degree (if applicable) |
| status      | ENUM(`Accepted`, `Rejected`, `Unclassified`, `Duplicated`) | Article classification status |

### **Other Tables**
- `journals` → Stores journal names.
- `authors` → Stores author names.
- `article_authors` → Links articles to authors.
- `keywords` → Stores unique keywords.
- `article_keywords` → Links articles to keywords.

---

## Exporting Data
After processing, the script automatically generates an **Excel file** (`articles_data.xlsx`) containing all articles.

```bash
python import_bibtex.py
```

This file can be opened in Excel or any spreadsheet software for further analysis.

---

## Example Console Output
```bash
Database 'articles_db' exists.
Existing tables were successfully dropped.
Tables created successfully.
Importing file: sample(3).bib
Importing file: sample(4).bib
Importing file: sample(5).bib
Importing file: sample(2).bib
Importing file: sample(1).bib
Importing file: sample(6).bib
Articles successfully inserted and linked with authors and journals.

Total records: 3478

Total articles by status:
Status               Total Articles
----------------------------------------
Unclassified         2910
Duplicated           568

Document type and total articles (Excluding Duplicates):
Document Type                  Total Articles
--------------------------------------------------
                               2408
 Article                       357
 research-article              90
 Article; Proceedings Paper    22
 Proceedings Paper             19
 Article; Early Access         4
 Article; Retracted Publication  4
 Editorial Material            2
 Review                        2
 Meeting Abstract              1
 Article; Data Paper           1

Excel file generated: articles_data.xlsx
```

---

## Notes
- If an article has a **DOI** that already exists in the database, it is marked as `Duplicated`.
- The script **removes duplicate authors and journals** by using `ON CONFLICT DO NOTHING` in SQL queries.
- The database structure is **automatically managed**, requiring no manual intervention.
