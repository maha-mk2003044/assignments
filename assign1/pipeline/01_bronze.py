
from pathlib import Path
from datetime import datetime, timezone
import uuid
import duckdb

# 1. Project paths
BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw" / "BACI_HS17"
LAKEHOUSE_DIR = BASE_DIR / "lakehouse"


# 2. Connect to DuckLake
con = duckdb.connect(str(LAKEHOUSE_DIR / "connection.duckdb"))
con.execute("LOAD ducklake;")

catalog_path = (LAKEHOUSE_DIR / "catalog.ducklake").as_posix()
storage_path = (LAKEHOUSE_DIR / "storage").as_posix() + "/"

con.execute(f"""
    ATTACH 'ducklake:{catalog_path}' AS lake
    (DATA_PATH '{storage_path}');
""")

# 3. Find annual BACI trade CSV files
files = sorted(RAW_DIR.glob("BACI_HS17_Y*.csv"))

if not files:
    raise FileNotFoundError(
        f"No BACI annual trade CSV files found in {RAW_DIR}"
    )

print(f"Found {len(files)} annual BACI files.")

# 4. Load each file into Bronze
for file in files:
    source_name = file.name

    # Skip files already successfully loaded
    already_loaded = con.execute("""
        SELECT COUNT(*)
        FROM lake.bronze.load_log
        WHERE source_name = ?
    """, [source_name]).fetchone()[0]

    if already_loaded:
        print(f"Skipping already loaded: {source_name}")
        continue

    load_id = str(uuid.uuid4())
    ingested_at = datetime.now(timezone.utc).replace(tzinfo=None)

    print(f"Loading {source_name} ...")


    # Read the CSV using its actual file path
    con.execute("""
        CREATE OR REPLACE TEMP VIEW source_csv AS
        SELECT
            t, i, j, k, v, q
        FROM read_csv(
            ?,
            header = true,
            all_varchar = true
        )
    """.replace("?", f"'{file.as_posix()}'"))


    input_count = con.execute("""
        SELECT COUNT(*) FROM source_csv
    """).fetchone()[0]

    # Make data insertion and logging one transaction
    con.execute("BEGIN TRANSACTION;")

    try:
        con.execute("""
            INSERT INTO lake.bronze.trade_raw
            SELECT
                t, i, j, k, v, q,
                ?, ?, ?
            FROM source_csv
        """, [source_name, ingested_at, load_id])

        con.execute("""
            INSERT INTO lake.bronze.load_log
            VALUES (?, ?, ?, ?)
        """, [load_id, source_name, input_count, ingested_at])

        con.execute("COMMIT;")

    except Exception:
        con.execute("ROLLBACK;")
        raise

    print(f"Loaded {input_count:,} rows.")

# 5. Display ingestion summary
summary = con.execute("""
    SELECT source_name, input_row_count
    FROM lake.bronze.load_log
    ORDER BY source_name
""").fetchall()

print("\nBronze ingestion summary:")
for name, count in summary:
    print(f"{name}: {count:,} rows")

total = con.execute("""
    SELECT COUNT(*) FROM lake.bronze.trade_raw
""").fetchone()[0]

print(f"\nTotal Bronze records: {total:,}")

con.close()
