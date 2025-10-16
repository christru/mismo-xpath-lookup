# MISMO XPath Lookup - NL2SQL with RAG Principles

A proof-of-concept demonstrating **Natural Language to SQL (NL2SQL)** for querying MISMO UniqueID Matrix data using natural language. This implementation uses RAG principles to ensure zero-hallucination exact data retrieval.

## What is NL2SQL and How Does It Relate to RAG?

**This tool uses NL2SQL (Natural Language to SQL) architecture:**
1. **Natural Language Understanding** (Claude AI) - Parses user intent into structured query parameters
2. **Direct Database Retrieval** (SQLite) - Executes exact SQL queries against 1.6M+ records
3. **Structured Output** - Returns precise data directly from the knowledge base

**Relationship to RAG:** This implements RAG's core principle of "retrieve from knowledge base rather than generate from LLM memory" - but instead of using retrieved context to generate an answer, it returns the exact database records. This makes it more accurate for exact lookups (IDs, XPaths) eliminating hallucination risk.

**Key Distinction:**
- **Traditional RAG**: Retrieves context → LLM generates answer based on context
- **This Tool (NL2SQL)**: Parses intent → Direct SQL query → Exact database results

## Architecture

```
User Query (Natural Language)
    ↓
Claude AI (Intent Parsing to JSON)
    ├─ Determines lookup type (by_unique_id, by_reference_id, by_xpath)
    └─ Extracts search value
    ↓
SQL Query (Direct Database Lookup)
    ↓
SQLite Database (1.6M+ records)
    ↓
Formatted Results (Exact data from source - no LLM generation)
```

## Features

- **Natural Language Interface** - Ask questions in plain English
- **Bidirectional Search** - Find XPath from ID or ID from XPath



## Why NL2SQL Instead of Pure LLM or Traditional RAG?

| Approach | Pros | Cons | Best For |
|----------|------|------|----------|
| **Pure LLM** | Natural conversation | Can hallucinate incorrect IDs/XPaths | General questions |
| **Traditional RAG** | Grounded in retrieved context | LLM still generates answer (risk of minor errors) | Explanations, summaries |
| **This Tool (NL2SQL)** | Zero hallucination - exact database results | Requires initial data import | Exact lookups (IDs, XPaths, versions) |

This example shows how to build a fact-based AI solution for technical documentation where **accuracy is required**.

## Prerequisites

- Python 3.7+
- Anthropic API key ([Get one here](https://console.anthropic.com/))
- **MISMO UniqueID Matrix Excel file** (see download instructions below)

## Installation

### 1. Clone this repository:
```cmd
git clone <your-repo-url>
cd mismo-xpath-lookup
```

### 2. Install dependencies:
```cmd
pip install -r requirements.txt
```

### 3. Download MISMO UniqueID Matrix

**Important**: Due to MISMO licensing restrictions, the UniqueID Matrix Excel file is NOT included in this repository.

MISMO members can download it from:
**https://www.mismo.org/standards-resources/mismo-product/mismo-version-3.6.2-reference-model**

Look for the file named something like: `UniqueID_Matrix_v3.6.2_B373.xlsx`

Place the downloaded Excel file in this project directory.

### 4. Add your Anthropic API key:

Open `xpath_lookup_poc.py` in a text editor and replace the API key on line 57:
```python
ANTHROPIC_API_KEY = "your-api-key-here"
```

## Quick Start

### 1. Import Data (One-Time Setup)

Once you've downloaded the MISMO Excel file, run:

```cmd
python xpath_lookup_poc.py --setup UniqueID_Matrix_v3.6.2_B373.xlsx
```

(Replace the filename with your actual downloaded file if different)

This will:
- Read the Excel file
- Process all Container and Data Point XPath sheets
- Create a local SQLite database (`xpath_data.db`)
- Import 1.6M+ records (takes ~2 minutes)

### 2. Query the Data

Use natural language queries:

```cmd
REM Find XPath by Unique ID
python xpath_lookup_poc.py "Get xpath for ID MC000001.00001"

REM Find all instances of a Reference ID
python xpath_lookup_poc.py "Show all instances of MD000001"

REM Reverse lookup - find ID from XPath
python xpath_lookup_poc.py "Find ID for MESSAGE/ABOUT_VERSIONS/ABOUT_VERSION"

REM XPath with leading slashes (automatically handled)
python xpath_lookup_poc.py "Find ID for //MESSAGE/ABOUT_VERSIONS/ABOUT_VERSION"
python xpath_lookup_poc.py "Find ID for /MESSAGE/ABOUT_VERSIONS/ABOUT_VERSION/"
```

## Query Examples

### By Unique ID
```cmd
python xpath_lookup_poc.py "What is the xpath for MC000001.00001?"
python xpath_lookup_poc.py "Lookup ID md004146.00161"
python xpath_lookup_poc.py "Get xpath for MC000001.00001"
```
*Note: Searches are case-insensitive*

### By Reference ID
```cmd
python xpath_lookup_poc.py "Show all instances of MC000001"
python xpath_lookup_poc.py "Find all MD000001 records"
python xpath_lookup_poc.py "List MC000001"
```

### By XPath (Reverse Lookup)
```cmd
python xpath_lookup_poc.py "Find ID for MESSAGE/ABOUT_VERSIONS/ABOUT_VERSION"
python xpath_lookup_poc.py "What uses xpath MESSAGE/DEAL_SETS/DEAL_SET"
```

## Output Format

```
Query: Get xpath for ID MC000001.00001

Understanding: by_unique_id -> 'MC000001.00001'

Found 1 result(s):

======================================================================
Result 1:
  Unique ID:    MC000001.00001
  Name:         ABOUT_VERSION
  Reference ID: MC000001
  Source:       Container XPaths

  XPath:
    MESSAGE/DOCUMENT_SETS/DOCUMENT_SET/.../ABOUT_VERSION

  Versions:
    Version 3.6.2: v3.6.2
    Version 3.6.1: v3.6.1
    Version 3.6.0: v3.6.0
    Version 3.5.0: v3.5.0
    Version 3.4.0: v3.4.0
    Version 3.3.1: v3.3.1
    Version 3.3.0: v3.3.0
    Version 3.2.0: N/A
    Version 3.1.0: N/A
    Version 3.0.0: N/A
```

## How It Works

1. **Natural Language Processing**: Your query is sent to Claude AI which determines:
   - Lookup type (by_unique_id, by_reference_id, or by_xpath)
   - Search value to use

2. **Database Query**: The tool queries the local SQLite database with:
   - Case-insensitive matching
   - Automatic xpath sanitization (removes leading/trailing slashes)

3. **Results Display**: Shows complete record information including:
   - Unique ID, Name, Reference ID
   - Full XPath (with data point name appended for data points)
   - Version availability across all MISMO versions

## Database Schema

The SQLite database contains one table: `xpath_records`

| Column         | Type | Description                                    |
|----------------|------|------------------------------------------------|
| sheet_source   | TEXT | Source sheet (Container/Data Point XPaths)    |
| unique_id      | TEXT | Full unique identifier (e.g., MC000001.00001) |
| name           | TEXT | Container or data point name                  |
| xpath          | TEXT | Full MISMO xpath                              |
| reference_id   | TEXT | Base ID without instance (e.g., MC000001)     |
| all_versions   | TEXT | JSON string of all version columns            |

**Note**: For Data Point sheets, the data point name is automatically appended to the xpath upon import.

## Project Structure

```
.
├── xpath_lookup_poc.py        # Main CLI tool
├── README.md                   # This file
├── requirements.txt            # Python dependencies
├── .gitignore                  # Git exclusions

# Files you create/download (not in repo):
├── xpath_data.db              # SQLite database (created after setup)
└── UniqueID_Matrix_*.xlsx     # MISMO Excel file (download from mismo.org)
```

**Note**: The MISMO Excel file and generated database are excluded from the repository due to licensing restrictions. Users must download the Excel file from MISMO's website.

## Understanding the NL2SQL Flow

1. **User Query**: "Get xpath for ID MC000001.00001"
2. **Claude Parsing (Intent → JSON)**: Identifies `lookup_type: "by_unique_id"` and `value: "MC000001.00001"`
3. **SQL Query Generation**: `SELECT * FROM xpath_records WHERE LOWER(unique_id) = LOWER('MC000001.00001')`
4. **Database Retrieval**: Exact record from MISMO matrix (1.6M+ records)
5. **Formatted Output**: Displays XPath, versions, and metadata

**Key Point:** The LLM only parses intent - it never generates the answer. Results come directly from the database with zero hallucination risk.

## Troubleshooting

### "Database not found"
Run the setup command first:
```cmd
python xpath_lookup_poc.py --setup UniqueID_Matrix_v3.6.2_B373.xlsx
```

### Import Errors
Make sure all dependencies are installed:
```cmd
pip install -r requirements.txt
```

## Technical Details

- **Language**: Python 3.7+
- **Database**: SQLite (local file, no server required)
- **AI Model**: Claude Haiku 4.5 (fast and cost-effective for intent parsing)
- **Data Processing**: Pandas for Excel import
- **Storage**: ~1000MB for 1.6M records
- **Architecture Pattern**: NL2SQL (Natural Language to SQL) with RAG principles

**The NL2SQL Pattern:** Natural Language → LLM Intent Parsing → SQL Query → Database Retrieval → Structured Output (no LLM generation)