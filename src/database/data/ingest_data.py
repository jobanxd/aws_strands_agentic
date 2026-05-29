import sqlite3
from pathlib import Path

import pandas as pd

# ============================================================================
# PATH SETUP
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent

DB_PATH = BASE_DIR / "kyc_database.db"

RAW_DIR = BASE_DIR / "raw"

MOCK_DATA_FILE = RAW_DIR / "mock_data.xlsx"
COUNTRY_RISK_FILE = RAW_DIR / "country_risk_classification.xlsx"
PROMPTS_FILE = RAW_DIR / "prompts.xlsx"

# ============================================================================
# SQLITE CONNECTION
# ============================================================================

conn = sqlite3.connect(DB_PATH)

# Enable foreign keys
conn.execute("PRAGMA foreign_keys = ON;")
cursor = conn.cursor()

# Disable FK checks temporarily for cleanup
cursor.execute("PRAGMA foreign_keys = OFF;")

tables_to_clear = [
    "user_odd_review_list",
    "kycnet_drilldown",
    "servicelink_transactions",
    "svoc_extracts",
    "sharepoint_list",
    "kycnet_reviews",
    "servicelink_account_details",
    "lu_country_risk_classification"
]

for table in tables_to_clear:
    cursor.execute(f"DELETE FROM {table};")

conn.commit()

# Re-enable FK checks
cursor.execute("PRAGMA foreign_keys = ON;")

# ============================================================================
# INGEST EXCEL SHEETS
# ============================================================================

def ingest_excel_sheets(excel_path: Path):
    """
    Read all sheets from an Excel file and insert them into SQLite tables.

    Rules:
    - Sheet name == table name
    - Excel headers == DB column names
    """

    if not excel_path.exists():
        print(f"File not found: {excel_path}")
        return

    print(f"\nProcessing workbook: {excel_path.name}")

    # Read all sheets
    excel_data = pd.read_excel(
        excel_path,
        sheet_name=None
    )

    for sheet_name, df in excel_data.items():

        print(f"\nIngesting sheet: {sheet_name}")

        # Replace NaN with None
        df = df.where(pd.notnull(df), None)

        print(df.columns.tolist())

        if sheet_name == "kycnet_drilldown":

            # Get mapping from sharepoint_list
            sharepoint_df = pd.read_sql_query(
                """
                SELECT
                    MIN(sharepoint_id) AS sharepoint_id,
                    party_id
                FROM sharepoint_list
                GROUP BY party_id
                """,
                conn
            )

            # Convert both keys to string
            df["party_id"] = df["party_id"].astype(str)
            sharepoint_df["party_id"] = sharepoint_df["party_id"].astype(str)

            # Merge to derive sharepoint_id
            df = df.merge(
                sharepoint_df,
                on="party_id",
                how="left"
            )


        try:
            # Insert into matching table
            df.to_sql(
                sheet_name,
                conn,
                if_exists="append",
                index=False
            )

            print(f"Inserted {len(df)} rows into '{sheet_name}'")

        except Exception as e:
            import traceback

            print(f"\nFailed to ingest '{sheet_name}'")
            print(f"Error type: {type(e).__name__}")
            print(f"Error details: {e}")

            traceback.print_exc()


# ============================================================================
# MAIN INGESTION
# ============================================================================

try:

    # Main mock workbook
    ingest_excel_sheets(MOCK_DATA_FILE)

    print("\nProcessing workbook: country_risk_classification.xlsx")

    df = pd.read_excel(
        COUNTRY_RISK_FILE,
        sheet_name="lu_country_risk_classification"
    )

    df = df.where(pd.notnull(df), None)

    df.to_sql(
        "lu_country_risk_classification",
        conn,
        if_exists="append",
        index=False
    )

    print(
        f"Inserted {len(df)} rows into "
        f"'lu_country_risk_classification'"
    )

    print("\nProcessing workbook: prompts.xlsx")

    df = pd.read_excel(
        PROMPTS_FILE,
        sheet_name="lu_agent_prompts"
    )

    df = df.where(pd.notnull(df), None)

    df.to_sql(
        "lu_agent_prompts",
        conn,
        if_exists="append",
        index=False
    )

    print(
        f"Inserted {len(df)} rows into "
        f"'lu_agent_prompts'"
    )

    conn.commit()

    print("\nData ingestion completed successfully!")

except Exception as e:
    print(f"\nFatal error: {e}")
#
finally:
    conn.close()
