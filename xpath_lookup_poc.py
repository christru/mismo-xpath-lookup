"""
MISMO XPath Lookup - NL2SQL with RAG Principles

This is a proof-of-concept demonstrating NL2SQL (Natural Language to SQL) architecture
for querying MISMO UniqueID Matrix data. It showcases how to combine:
1. A local knowledge base (1.6M+ records in SQLite)
2. Natural language understanding (Claude AI for intent parsing)
3. Direct database retrieval (zero-hallucination exact results)

The tool uses Claude to parse user intent from natural language queries into structured
parameters, then executes direct SQL queries against a local database. This implements
RAG's core principle of "retrieve from knowledge base" but returns exact database records
rather than LLM-generated answers - ensuring 100% accuracy for exact lookups.

NL2SQL Architecture:
    User Query (Natural Language)
        ↓
    Claude AI (Parse intent → JSON with lookup_type + value)
        ↓
    SQL Query (Direct database lookup - no LLM generation)
        ↓
    SQLite Database (Retrieve exact records from 1.6M+ entries)
        ↓
    Formatted Results (Exact data from source)

Key Distinction from Traditional RAG:
- Traditional RAG: Retrieves context → LLM generates answer
- This Tool: Parses intent → Direct SQL query → Exact results (no generation)

Features:
- Natural language to structured query conversion
- Bidirectional lookups (ID→XPath or XPath→ID)
- Case-insensitive search with automatic sanitization
- Complete version history across MISMO 3.0.0 - 3.6.2
- Zero hallucination risk (results come directly from database)

Usage:
    # First-time setup
    python xpath_lookup_poc.py --setup UniqueID_Matrix_v3.6.2_B373.xlsx

    # Query examples
    python xpath_lookup_poc.py "Get xpath for ID MC000001.00001"
    python xpath_lookup_poc.py "Show all instances of MD000001"
    python xpath_lookup_poc.py "Find ID for MESSAGE/ABOUT_VERSIONS/ABOUT_VERSION"

For more information, see README.md
"""

import sqlite3
import json
import sys
import re
import pandas as pd
from anthropic import Anthropic
from pathlib import Path

# =============================================================================
# CONFIGURATION
# =============================================================================

# Database file path
DB_PATH = "xpath_data.db"

# Anthropic API Key - Replace with your key from https://console.anthropic.com/
ANTHROPIC_API_KEY = "your-api-key-here"

# Excel sheet names to import
SHEETS_TO_IMPORT = [
    "Container XPaths",
    "Data Point XPaths (1-1m)",
    "Data Point XPaths (1m+)"
]


# =============================================================================
# DATABASE SETUP
# =============================================================================

def setup_database(excel_path: str):
    """
    Import MISMO UniqueID Matrix Excel file into SQLite database.

    This function reads the specified Excel file, processes Container XPaths and
    Data Point XPaths sheets, normalizes the data, and stores it in a local SQLite
    database for fast querying.

    Args:
        excel_path: Path to the MISMO UniqueID Matrix Excel file

    Database Schema:
        - sheet_source: Source sheet name (Container/Data Point XPaths)
        - unique_id: Full unique identifier (e.g., MC000001.00001)
        - name: Container or data point name
        - xpath: Full MISMO xpath (data points have name appended)
        - reference_id: Base ID without instance number (e.g., MC000001)
        - all_versions: JSON string of all version columns

    Note:
        - For Data Point sheets, the data point name is appended to the xpath upon import
        - Container sheets keep xpath as-is
        - All existing data is dropped and recreated on each setup
    """
    print(f"Importing {excel_path}...\n")

    xl_file = pd.ExcelFile(excel_path)
    conn = sqlite3.connect(DB_PATH)

    # Drop existing table if it exists
    conn.execute("DROP TABLE IF EXISTS xpath_records")

    total_rows = 0

    for sheet_name in SHEETS_TO_IMPORT:
        if sheet_name not in xl_file.sheet_names:
            print(f"  WARNING: Sheet '{sheet_name}' not found, skipping...")
            continue

        print(f"  Processing: {sheet_name}")
        df = pd.read_excel(xl_file, sheet_name=sheet_name)

        # Normalize column names
        df.columns = df.columns.str.strip()

        # Determine xpath column name (different between sheets)
        xpath_col = 'XPath' if 'XPath' in df.columns else 'DatapointUsageXPath'

        # Get name column
        name_col = 'Container Name' if 'Container Name' in df.columns else 'Data Point Name'

        # Get all version columns dynamically
        version_cols = [col for col in df.columns if col.startswith('Version')]

        # For Data Point sheets, append the data point name to the xpath
        is_datapoint_sheet = 'Data Point' in sheet_name
        if is_datapoint_sheet:
            # Append data point name to the end of each xpath
            xpaths = df[xpath_col] + '/' + df[name_col]
        else:
            # Container sheets - use xpath as-is
            xpaths = df[xpath_col]

        # Create normalized structure with base fields
        normalized = pd.DataFrame({
            'sheet_source': sheet_name,
            'unique_id': df['Unique ID'],
            'name': df[name_col],
            'xpath': xpaths,
            'reference_id': df['Reference ID'],
        })

        # Add all version columns as JSON for complete history
        version_history = df[version_cols].to_dict('records')
        normalized['all_versions'] = [json.dumps(v) for v in version_history]

        # Save to database
        normalized.to_sql('xpath_records', conn, if_exists='append', index=False)
        total_rows += len(normalized)
        print(f"    Imported {len(normalized)} rows")

    conn.commit()
    conn.close()

    print(f"\nSetup complete! {total_rows} total records imported.\n")


# =============================================================================
# QUERY FUNCTIONS
# =============================================================================

def lookup_by_id(unique_id: str):
    """
    Find record by Unique ID.

    Args:
        unique_id: Full unique identifier (e.g., MC000001.00001)

    Returns:
        sqlite3.Row object with record data, or None if not found

    Note:
        Search is case-insensitive
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # Case-insensitive search
    cursor.execute("SELECT * FROM xpath_records WHERE LOWER(unique_id) = LOWER(?)", (unique_id,))
    result = cursor.fetchone()
    conn.close()
    return result


def lookup_by_xpath(xpath: str):
    """
    Find records by XPath (reverse lookup).

    Args:
        xpath: MISMO xpath to search for

    Returns:
        List of sqlite3.Row objects matching the xpath

    Note:
        - Search is case-insensitive
        - Leading //, /, and trailing / are automatically stripped
        - Examples: "//MESSAGE/...", "/MESSAGE/...", "MESSAGE/..." all work
    """
    # Sanitize xpath: remove leading // or / and trailing /
    xpath = xpath.strip()
    if xpath.startswith('//'):
        xpath = xpath[2:]
    xpath = xpath.strip('/')

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # Case-insensitive search
    cursor.execute("SELECT * FROM xpath_records WHERE LOWER(xpath) = LOWER(?)", (xpath,))
    results = cursor.fetchall()
    conn.close()
    return results


def lookup_by_reference_id(ref_id: str):
    """
    Find all instances of a Reference ID.

    Args:
        ref_id: Base reference ID without instance number (e.g., MC000001)

    Returns:
        List of sqlite3.Row objects, sorted by unique_id

    Example:
        lookup_by_reference_id("MC000001") returns all MC000001.00001,
        MC000001.00002, etc.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM xpath_records WHERE reference_id = ? ORDER BY unique_id", 
        (ref_id,)
    )
    results = cursor.fetchall()
    conn.close()
    return results


# =============================================================================
# NATURAL LANGUAGE PROCESSING
# =============================================================================

def parse_query(user_input: str):
    """
    Parse natural language query using Claude AI to determine lookup type and value.

    This is the NL2SQL "intent parsing" step - Claude interprets the user's natural
    language and extracts structured parameters (lookup_type + value) that are used to
    construct SQL queries for exact database retrieval. The LLM never generates the
    answer - it only parses intent.

    Args:
        user_input: Natural language query from user

    Returns:
        dict: Contains 'lookup_type' and 'value'
              lookup_type: One of "by_unique_id", "by_reference_id", "by_xpath"
              value: The search value extracted from the query

    Raises:
        json.JSONDecodeError: If Claude returns invalid JSON

    Examples:
        "Get xpath for ID MC000001.00001" → {"lookup_type": "by_unique_id", "value": "MC000001.00001"}
        "Show all MC000001" → {"lookup_type": "by_reference_id", "value": "MC000001"}
    """
    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": f"""Parse this MISMO xpath lookup query and return JSON:
- lookup_type: "by_unique_id" | "by_reference_id" | "by_xpath"
- value: the search value

Examples:
"Get xpath for ID MC000001.00001" → {{"lookup_type": "by_unique_id", "value": "MC000001.00001"}}
"Show all instances of MC000001" → {{"lookup_type": "by_reference_id", "value": "MC000001"}}
"Find ID for MESSAGE/DEAL_SETS/..." → {{"lookup_type": "by_xpath", "value": "MESSAGE/DEAL_SETS/..."}}

Query: {user_input}

Return only JSON."""
        }]
    )

    # Extract text from response
    response_text = response.content[0].text.strip()

    # Try to extract JSON from response (handles cases where Claude adds explanation text)
    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    if json_match:
        response_text = json_match.group(0)

    return json.loads(response_text)


# =============================================================================
# OUTPUT FORMATTING
# =============================================================================

def display_results(results, lookup_type):
    """
    Display query results in a formatted, human-readable format.

    Args:
        results: Single sqlite3.Row or list of sqlite3.Row objects
        lookup_type: Type of lookup performed (for potential future use)

    Output includes:
        - Unique ID, Name, Reference ID, Source sheet
        - Full XPath
        - Version history (all MISMO versions from 3.0.0 to 3.6.2)
    """
    if not results:
        print("No results found.\n")
        return

    # Handle single result
    if not isinstance(results, list):
        results = [results]

    print(f"\nFound {len(results)} result(s):\n")

    for i, row in enumerate(results, 1):
        print(f"{'='*70}")
        print(f"Result {i}:")
        print(f"  Unique ID:    {row['unique_id']}")
        print(f"  Name:         {row['name']}")
        print(f"  Reference ID: {row['reference_id']}")
        print(f"  Source:       {row['sheet_source']}")
        print(f"\n  XPath:")
        print(f"    {row['xpath']}")

        # Parse and display all versions from JSON
        if row['all_versions']:
            try:
                versions = json.loads(row['all_versions'])
                if versions:
                    print(f"\n  Versions:")
                    # Sort version keys in reverse order (newest first)
                    version_items = sorted(versions.items(), reverse=True)
                    for version_key, version_value in version_items:
                        # Show all versions, display N/A for nan/empty values
                        if not version_value or str(version_value).strip() == '' or str(version_value).lower() == 'nan':
                            print(f"    {version_key}: N/A")
                        else:
                            print(f"    {version_key}: {version_value}")
            except (json.JSONDecodeError, TypeError):
                print(f"\n  Versions: Unable to parse version data")

        print()


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """
    Main CLI entry point.

    Handles two modes:
    1. Setup mode: --setup <excel_file>
    2. Query mode: Natural language query

    Exit codes:
        0: Success
        1: Error (printed to stderr)
    """
    # Get query from command line
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python xpath_lookup.py --setup UniqueID_Matrix_v3.6.2_B373.xlsx")
        print("\nQuery examples:")
        print("  python xpath_lookup.py 'Get xpath for ID MC000001.00001'")
        print("  python xpath_lookup.py 'Show all instances of MD000001'")
        print("  python xpath_lookup.py 'Find ID for MESSAGE/ABOUT_VERSIONS/ABOUT_VERSION'")
        return

    # Handle setup (check this BEFORE checking database existence)
    if sys.argv[1] == "--setup":
        if len(sys.argv) < 3:
            print("ERROR: Please provide Excel file path")
            return
        setup_database(sys.argv[2])
        return

    # Check if database exists (only for query operations)
    if not Path(DB_PATH).exists():
        print("WARNING: Database not found. Run setup first:")
        print("   python xpath_lookup.py --setup UniqueID_Matrix_v3.6.2_B373.xlsx\n")
        return

    # Process query
    user_query = " ".join(sys.argv[1:])
    print(f"Query: {user_query}\n")

    try:
        # Parse with Claude
        intent = parse_query(user_query)
        print(f"Understanding: {intent['lookup_type']} -> '{intent['value']}'")

        # Execute lookup
        if intent['lookup_type'] == 'by_unique_id':
            results = lookup_by_id(intent['value'])
        elif intent['lookup_type'] == 'by_reference_id':
            results = lookup_by_reference_id(intent['value'])
        elif intent['lookup_type'] == 'by_xpath':
            results = lookup_by_xpath(intent['value'])
        else:
            print(f"ERROR: Unknown lookup type '{intent['lookup_type']}'\n")
            return

        display_results(results, intent['lookup_type'])

    except Exception as e:
        print(f"ERROR: {e}\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()