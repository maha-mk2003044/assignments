
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

print("Starting Silver processing...")

# 1. Extract Qatar imports from Bronze.
# Keep original text values for validation.
con.execute("""
    CREATE OR REPLACE TEMP TABLE qatar_source AS
    SELECT t, i, j, k, v, q, source_name, load_id
    FROM lake.bronze.trade_raw
    WHERE TRY_CAST(j AS INTEGER) = 634
""")

bronze_qatar_count = con.execute("""
    SELECT COUNT(*) FROM qatar_source
""").fetchone()[0]

print(f"Qatar Bronze records: {bronze_qatar_count:,}")

# 2. Convert types and identify duplicates.
con.execute("""
    CREATE OR REPLACE TEMP TABLE validated AS
    SELECT *,
        TRY_CAST(t AS INTEGER) AS clean_year,
        TRY_CAST(i AS INTEGER) AS clean_exporter,
        TRY_CAST(j AS INTEGER) AS clean_importer,
        LPAD(TRIM(k), 6, '0') AS clean_product,
        TRY_CAST(v AS DOUBLE) AS clean_value,
        TRY_CAST(q AS DOUBLE) AS clean_quantity,

        ROW_NUMBER() OVER (
            PARTITION BY t, i, j, k
            ORDER BY source_name, load_id
        ) AS duplicate_rank
    FROM qatar_source
""")

# 3. Assign validation failures.
con.execute("""
    CREATE OR REPLACE TEMP TABLE classified AS
    SELECT *,
        CASE
            WHEN clean_year IS NULL
                OR clean_year NOT BETWEEN 2017 AND 2024
                THEN 'Invalid year'

            WHEN clean_exporter IS NULL
                OR clean_importer != 634
                THEN 'Invalid country code'

            WHEN k IS NULL
                OR NOT REGEXP_FULL_MATCH(TRIM(k), '[0-9]{1,6}')
                THEN 'Invalid product code'

            WHEN clean_value IS NULL
                OR clean_value < 0
                THEN 'Invalid trade value'

            WHEN clean_quantity < 0
                THEN 'Negative quantity'

            WHEN duplicate_rank > 1
                THEN 'Duplicate business key'

            ELSE NULL
        END AS rejection_reason
    FROM validated
""")

# 4. Clear previous Silver results for safe reruns.
con.execute("BEGIN TRANSACTION;")

try:
    con.execute("DELETE FROM lake.silver.qatar_imports")
    con.execute("DELETE FROM lake.silver.quarantine")
    con.execute("DELETE FROM lake.silver.quality_report")

    # 5. Insert valid records.
    con.execute("""
        INSERT INTO lake.silver.qatar_imports
        SELECT
            clean_year,
            clean_exporter,
            clean_importer,
            clean_product,
            clean_value,
            clean_quantity,
            source_name,
            load_id
        FROM classified
        WHERE rejection_reason IS NULL
    """)

    # 6. Quarantine rejected records.
    con.execute("""
        INSERT INTO lake.silver.quarantine
        SELECT
            t, i, j, k, v, q,
            source_name,
            load_id,
            rejection_reason
        FROM classified
        WHERE rejection_reason IS NOT NULL
    """)

    # 7. Store data-quality metrics.
    con.execute("""
        INSERT INTO lake.silver.quality_report
        SELECT 'bronze_total_rows',
               (SELECT COUNT(*) FROM lake.bronze.trade_raw)
        UNION ALL
        SELECT 'bronze_qatar_rows',
               (SELECT COUNT(*) FROM qatar_source)
        UNION ALL
        SELECT 'silver_valid_rows',
               (SELECT COUNT(*) FROM lake.silver.qatar_imports)
        UNION ALL
        SELECT 'quarantine_rows',
               (SELECT COUNT(*) FROM lake.silver.quarantine)
        UNION ALL
        SELECT 'duplicate_rows',
               (SELECT COUNT(*) FROM classified
                WHERE duplicate_rank > 1)
        UNION ALL
        SELECT 'null_key_rows',
               (SELECT COUNT(*) FROM classified
                WHERE clean_year IS NULL
                   OR clean_exporter IS NULL
                   OR clean_importer IS NULL
                   OR k IS NULL)
        UNION ALL
        SELECT 'silver_null_quantity',
               (SELECT COUNT(*)
               FROM lake.silver.qatar_imports
                WHERE quantity IS NULL)

        UNION ALL
        SELECT 'silver_duplicate_keys',
               (SELECT COUNT(*) FROM (
                    SELECT year, exporter_code,
                           importer_code, product_code
                    FROM lake.silver.qatar_imports
                    GROUP BY 1, 2, 3, 4
                    HAVING COUNT(*) > 1
               ))
    """)

    con.execute("COMMIT;")

except Exception:
    con.execute("ROLLBACK;")
    raise

# 8. Print quality report.
print("\nSILVER DATA QUALITY REPORT")
print("-" * 40)

results = con.execute("""
    SELECT metric, metric_value
    FROM lake.silver.quality_report
""").fetchall()

for metric, value in results:
    print(f"{metric}: {value:,}")

print("\nQUARANTINE REASONS")
print("-" * 40)

reasons = con.execute("""
    SELECT rejection_reason, COUNT(*) AS rejected_rows
    FROM lake.silver.quarantine
    GROUP BY rejection_reason
    ORDER BY rejected_rows DESC
""").fetchall()

for reason, count in reasons:
    print(f"{reason}: {count:,}")

con.close()

print("\nSilver processing completed!")
