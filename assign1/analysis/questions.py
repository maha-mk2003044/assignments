
from pathlib import Path
import duckdb
import pandas as pd
import matplotlib.pyplot as plt

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

# Question 1: Annual import value into Qatar
q1 = con.execute("""
    SELECT
        y.year,
        ROUND(SUM(f.trade_value), 2) AS total_import_value
    FROM lake.gold.fact_imports f
    JOIN lake.gold.dim_year y
        ON f.year_key = y.year_key
    GROUP BY y.year
    ORDER BY y.year
""").df()

print("\nQUESTION 1: Qatar's Annual Import Value")
print(q1.to_string(index=False))

# Visualization 1: Line chart
plt.figure(figsize=(9, 5))
plt.plot(
    q1["year"],
    q1["total_import_value"],
    marker="o"
)
plt.title("Qatar's Annual Import Value (2017–2024)")
plt.xlabel("Year")
plt.ylabel("Import Value (BACI units)")
plt.xticks(q1["year"])
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(BASE_DIR / "analysis/figures/q1_import_trend.png", dpi=300, bbox_inches="tight")
plt.show()



# Question 2: Top 10 exporters to Qatar
q2 = con.execute("""
    SELECT
        e.country_name AS exporter_country,
        ROUND(SUM(f.trade_value), 2) AS total_import_value
    FROM lake.gold.fact_imports f
    JOIN lake.gold.dim_exporter e
        ON f.exporter_key = e.exporter_key
    GROUP BY e.exporter_key, e.country_name
    ORDER BY total_import_value DESC
    LIMIT 10
""").df()

print("\nQUESTION 2: Top 10 Exporters to Qatar (2017–2024)")
print(q2.to_string(index=False))

# Visualization 2: Horizontal bar chart
plt.figure(figsize=(10, 6))
plt.barh(
    q2["exporter_country"],
    q2["total_import_value"]
)
plt.gca().invert_yaxis()
plt.title("Top 10 Exporters to Qatar (2017–2024)")
plt.xlabel("Total Import Value (BACI units)")
plt.ylabel("Exporter Country")
plt.tight_layout()
plt.savefig(BASE_DIR / "analysis/figures/q2_top_exporters.png", dpi=300, bbox_inches="tight")
plt.show()



# Question 3: Top 10 imported HS17 products
q3 = con.execute("""
    SELECT
        p.product_key AS hs17_code,
        p.product_description AS product,
        ROUND(SUM(f.trade_value), 2) AS total_import_value
    FROM lake.gold.fact_imports f
    JOIN lake.gold.dim_product p
        ON f.product_key = p.product_key
    GROUP BY p.product_key, p.product_description
    ORDER BY total_import_value DESC
    LIMIT 10
""").df()

print("\nQUESTION 3: Top 10 Imported Products (2017–2024)")
print(q3.to_string(index=False))

# Visualization 3: Top 10 imported products
plt.figure(figsize=(11, 7))

labels = [
    f"{row.hs17_code} - {row.product[:45]}"
    for row in q3.itertuples()
]

plt.barh(
    labels,
    q3["total_import_value"]
)

plt.gca().invert_yaxis()
plt.title("Qatar's Top 10 Imported HS17 Products (2017–2024)")
plt.xlabel("Total Import Value (BACI units)")
plt.ylabel("HS17 Product")
plt.tight_layout()

# Save the figure
plt.savefig(
    BASE_DIR / "analysis/figures/q3_top_products.png",
    dpi=300,
    bbox_inches="tight"
)

plt.show()



# Question 4: Annual import shares of the top 5 suppliers
q4 = con.execute("""
    WITH top_five AS (
        SELECT exporter_key
        FROM lake.gold.fact_imports
        GROUP BY exporter_key
        ORDER BY SUM(trade_value) DESC
        LIMIT 5
    ),
    annual_totals AS (
        SELECT
            year_key,
            SUM(trade_value) AS annual_total
        FROM lake.gold.fact_imports
        GROUP BY year_key
    ),
    supplier_totals AS (
        SELECT
            f.year_key,
            f.exporter_key,
            SUM(f.trade_value) AS supplier_total
        FROM lake.gold.fact_imports f
        JOIN top_five t
            ON f.exporter_key = t.exporter_key
        GROUP BY f.year_key, f.exporter_key
    )
    SELECT
        y.year,
        e.country_name AS exporter_country,
        ROUND(
            100.0 * s.supplier_total
            / NULLIF(a.annual_total, 0),
            2
        ) AS import_share_pct
    FROM supplier_totals s
    JOIN annual_totals a
        ON s.year_key = a.year_key
    JOIN lake.gold.dim_year y
        ON s.year_key = y.year_key
    JOIN lake.gold.dim_exporter e
        ON s.exporter_key = e.exporter_key
    ORDER BY y.year, exporter_country
""").df()

print("\nQUESTION 4: Annual Import Shares of Top 5 Suppliers")
print(q4.to_string(index=False))

# Visualization 4: Supplier market share trends
plt.figure(figsize=(10, 6))

for country, group in q4.groupby("exporter_country"):
    plt.plot(
        group["year"],
        group["import_share_pct"],
        marker="o",
        label=country
    )

plt.title("Top 5 Suppliers' Shares of Qatar Imports (2017–2024)")
plt.xlabel("Year")
plt.ylabel("Share of Annual Import Value (%)")
plt.xticks(sorted(q4["year"].unique()))
plt.legend(title="Exporter Country")
plt.grid(alpha=0.3)
plt.tight_layout()

plt.savefig(
    BASE_DIR / "analysis/figures/q4_supplier_shares.png",
    dpi=300,
    bbox_inches="tight"
)

plt.show()



con.close()
