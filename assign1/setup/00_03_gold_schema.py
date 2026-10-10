
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

# Dimension 1: Year
con.execute("""
    CREATE TABLE IF NOT EXISTS lake.gold.dim_year (
        year_key INTEGER,
        year INTEGER
    );
""")

# Dimension 2: Exporter country
con.execute("""
    CREATE TABLE IF NOT EXISTS lake.gold.dim_exporter (
        exporter_key INTEGER,
        country_name VARCHAR,
        country_iso3 VARCHAR
    );
""")

# Dimension 3: HS17 product
con.execute("""
    CREATE TABLE IF NOT EXISTS lake.gold.dim_product (
        product_key VARCHAR,
        product_description VARCHAR
    );
""")

# Fact table: Qatar's annual imports
con.execute("""
    CREATE TABLE IF NOT EXISTS lake.gold.fact_imports (
        year_key INTEGER,
        exporter_key INTEGER,
        product_key VARCHAR,
        trade_value DOUBLE,
        quantity DOUBLE
    );
""")

print("Gold star schema tables created successfully!")
con.close()
