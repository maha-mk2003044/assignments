
from pathlib import Path
import duckdb

# 1. Project directories
BASE_DIR = Path(__file__).resolve().parents[1]
LAKEHOUSE_DIR = BASE_DIR / "lakehouse"
DATA_DIR = LAKEHOUSE_DIR / "storage"

LAKEHOUSE_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 2. Connect to DuckDB
con = duckdb.connect(str(LAKEHOUSE_DIR / "connection.duckdb"))

# 3. Install and load DuckLake
con.execute("INSTALL ducklake;")
con.execute("LOAD ducklake;")

# 4. Attach the DuckLake catalog
catalog_path = (LAKEHOUSE_DIR / "catalog.ducklake").as_posix()
storage_path = DATA_DIR.as_posix() + "/"

con.execute(f"""
    ATTACH 'ducklake:{catalog_path}' AS lake
    (DATA_PATH '{storage_path}');
""")

# 5. Create Medallion schemas
con.execute("CREATE SCHEMA IF NOT EXISTS lake.bronze;")
con.execute("CREATE SCHEMA IF NOT EXISTS lake.silver;")
con.execute("CREATE SCHEMA IF NOT EXISTS lake.gold;")

# 6. Verify setup
schemas = con.execute("""
    SELECT schema_name
    FROM information_schema.schemata
    WHERE catalog_name = 'lake'
    ORDER BY schema_name
""").fetchall()

print("DuckLake initialized successfully!")
print("Lakehouse location:", LAKEHOUSE_DIR)
print("Schemas:", schemas)

con.close()
