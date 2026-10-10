
from pathlib import Path
import duckdb

# 1. Project paths
BASE_DIR = Path(__file__).resolve().parents[1]
LAKEHOUSE_DIR = BASE_DIR / "lakehouse"
RAW_DIR = BASE_DIR / "data" / "raw" / "BACI_HS17"

COUNTRY_FILE = RAW_DIR / "country_codes_V202601.csv"
PRODUCT_FILE = RAW_DIR / "product_codes_HS17_V202601.csv"

# 2. Connect to DuckLake
con = duckdb.connect(str(LAKEHOUSE_DIR / "connection.duckdb"))
con.execute("LOAD ducklake;")

catalog_path = (LAKEHOUSE_DIR / "catalog.ducklake").as_posix()
storage_path = (LAKEHOUSE_DIR / "storage").as_posix() + "/"

con.execute(f"""
    ATTACH 'ducklake:{catalog_path}' AS lake
    (DATA_PATH '{storage_path}');
""")

print("Starting Gold processing...")

# 3. Load lookup CSVs into temporary tables
con.execute("""
    CREATE OR REPLACE TEMP TABLE country_lookup AS
    SELECT
        TRY_CAST(country_code AS INTEGER) AS country_code,
        country_name,
        country_iso3
    FROM read_csv(?, header = true, all_varchar = true)
""", [str(COUNTRY_FILE)])

con.execute("""
    CREATE OR REPLACE TEMP TABLE product_lookup AS
    SELECT
        LPAD(TRIM(code), 6, '0') AS product_code,
        description
    FROM read_csv(?, header = true, all_varchar = true)
""", [str(PRODUCT_FILE)])

# 4. Rebuild Gold tables for safe reruns
con.execute("BEGIN TRANSACTION;")

try:
    con.execute("DELETE FROM lake.gold.fact_imports")
    con.execute("DELETE FROM lake.gold.dim_year")
    con.execute("DELETE FROM lake.gold.dim_exporter")
    con.execute("DELETE FROM lake.gold.dim_product")

    # Dimension 1: Years
    con.execute("""
        INSERT INTO lake.gold.dim_year
        SELECT DISTINCT year, year
        FROM lake.silver.qatar_imports
    """)

    # Dimension 2: Exporter countries
    con.execute("""
        INSERT INTO lake.gold.dim_exporter
        SELECT DISTINCT
            s.exporter_code,
            COALESCE(c.country_name, 'Unknown'),
            c.country_iso3
        FROM (
            SELECT DISTINCT exporter_code
            FROM lake.silver.qatar_imports
        ) s
        LEFT JOIN country_lookup c
            ON s.exporter_code = c.country_code
    """)

    # Dimension 3: HS17 products
    con.execute("""
        INSERT INTO lake.gold.dim_product
        SELECT DISTINCT
            s.product_code,
            COALESCE(p.description, 'Unknown product')
        FROM (
            SELECT DISTINCT product_code
            FROM lake.silver.qatar_imports
        ) s
        LEFT JOIN product_lookup p
            ON s.product_code = p.product_code
    """)

    # Fact table: Qatar imports
    con.execute("""
        INSERT INTO lake.gold.fact_imports
        SELECT
            year,
            exporter_code,
            product_code,
            trade_value,
            quantity
        FROM lake.silver.qatar_imports
    """)

    con.execute("COMMIT;")

except Exception:
    con.execute("ROLLBACK;")
    raise

# 5. Validate Gold tables
print("\nGOLD TABLE ROW COUNTS")
print("-" * 40)

tables = [
    "dim_year",
    "dim_exporter",
    "dim_product",
    "fact_imports"
]

for table in tables:
    count = con.execute(
        f"SELECT COUNT(*) FROM lake.gold.{table}"
    ).fetchone()[0]
    print(f"{table}: {count:,}")

# 6. Verify fact and Silver counts match
silver_count = con.execute("""
    SELECT COUNT(*) FROM lake.silver.qatar_imports
""").fetchone()[0]

fact_count = con.execute("""
    SELECT COUNT(*) FROM lake.gold.fact_imports
""").fetchone()[0]

print("\nSilver records:", f"{silver_count:,}")
print("Gold fact records:", f"{fact_count:,}")

if silver_count != fact_count:
    raise ValueError("Silver and Gold row counts do not match!")

# 7. Check missing foreign-key references
missing_keys = con.execute("""
    SELECT COUNT(*)
    FROM lake.gold.fact_imports f
    LEFT JOIN lake.gold.dim_year y
        ON f.year_key = y.year_key
    LEFT JOIN lake.gold.dim_exporter e
        ON f.exporter_key = e.exporter_key
    LEFT JOIN lake.gold.dim_product p
        ON f.product_key = p.product_key
    WHERE y.year_key IS NULL
       OR e.exporter_key IS NULL
       OR p.product_key IS NULL
""").fetchone()[0]

print("Missing foreign-key references:", missing_keys)

if missing_keys > 0:
    raise ValueError("Gold contains invalid foreign-key references!")

# 8. Check dimension primary-key uniqueness
print("\nGOLD KEY UNIQUENESS CHECKS")
print("-" * 40)

dimension_checks = [
    ("dim_year", "year_key"),
    ("dim_exporter", "exporter_key"),
    ("dim_product", "product_key")
]

for table, key in dimension_checks:
    duplicates = con.execute(f"""
        SELECT COUNT(*)
        FROM (
            SELECT {key}
            FROM lake.gold.{table}
            GROUP BY {key}
            HAVING COUNT(*) > 1
        )
    """).fetchone()[0]

    null_keys = con.execute(f"""
        SELECT COUNT(*)
        FROM lake.gold.{table}
        WHERE {key} IS NULL
    """).fetchone()[0]

    print(f"{table}: duplicate PKs = {duplicates}, NULL PKs = {null_keys}")

    if duplicates > 0 or null_keys > 0:
        raise ValueError(f"Invalid primary keys in {table}")

# 9. Verify fact-table grain
fact_duplicates = con.execute("""
    SELECT COUNT(*)
    FROM (
        SELECT year_key, exporter_key, product_key
        FROM lake.gold.fact_imports
        GROUP BY 1, 2, 3
        HAVING COUNT(*) > 1
    )
""").fetchone()[0]

print("Duplicate fact business keys:", fact_duplicates)

if fact_duplicates > 0:
    raise ValueError("Fact table contains duplicate business keys!")

print("All Gold integrity checks passed!")

con.close()
print("\nGold processing completed successfully!")
