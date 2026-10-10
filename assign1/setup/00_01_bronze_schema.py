
from pathlib import Path
import duckdb

# Locate the project and existing DuckLake catalog
BASE_DIR = Path(__file__).resolve().parents[1]
LAKEHOUSE_DIR = BASE_DIR / "lakehouse"

con = duckdb.connect(str(LAKEHOUSE_DIR / "connection.duckdb"))
con.execute("LOAD ducklake;")

catalog_path = (LAKEHOUSE_DIR / "catalog.ducklake").as_posix()
storage_path = (LAKEHOUSE_DIR / "storage").as_posix() + "/"

con.execute(f"""
    ATTACH 'ducklake:{catalog_path}' AS lake
    (DATA_PATH '{storage_path}');
""")

# Raw BACI trade data, with ingestion metadata
con.execute("""
    CREATE TABLE IF NOT EXISTS lake.bronze.trade_raw (
        t VARCHAR,
        i VARCHAR,
        j VARCHAR,
        k VARCHAR,
        v VARCHAR,
        q VARCHAR,
        source_name VARCHAR,
        ingested_at TIMESTAMP,
        load_id VARCHAR
    );
""")

# Record each source file and its input row count
con.execute("""
    CREATE TABLE IF NOT EXISTS lake.bronze.load_log (
        load_id VARCHAR,
        source_name VARCHAR,
        input_row_count BIGINT,
        ingested_at TIMESTAMP
    );
""")

print("Bronze schema tables created successfully!")
con.close()
