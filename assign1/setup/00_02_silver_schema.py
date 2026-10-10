
from pathlib import Path
import duckdb

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

# Clean, validated Qatar import records
con.execute("""
    CREATE TABLE IF NOT EXISTS lake.silver.qatar_imports (
        year INTEGER,
        exporter_code INTEGER,
        importer_code INTEGER,
        product_code VARCHAR,
        trade_value DOUBLE,
        quantity DOUBLE,
        source_name VARCHAR,
        load_id VARCHAR
    );
""")

# Rejected records and their reasons
con.execute("""
    CREATE TABLE IF NOT EXISTS lake.silver.quarantine (
        t VARCHAR,
        i VARCHAR,
        j VARCHAR,
        k VARCHAR,
        v VARCHAR,
        q VARCHAR,
        source_name VARCHAR,
        load_id VARCHAR,
        rejection_reason VARCHAR
    );
""")

# Data quality metrics
con.execute("""
    CREATE TABLE IF NOT EXISTS lake.silver.quality_report (
        metric VARCHAR,
        metric_value BIGINT
    );
""")

print("Silver schema tables created successfully!")
con.close()
