# Qatar Import Trade Data Lakehouse (2017–2024)

## 1. Homework Overview

This homework implements a Bronze–Silver–Gold data lakehouse using DuckDB and DuckLake to analyze Qatar's international merchandise imports from 2017 to 2024.

The homework uses the CEPII BACI HS17 dataset, which contains international trade records classified by exporter country, importer country, product, and year.

The analysis focuses on Qatar (country code 634) and investigates import trends, major trading partners, leading imported products, and changes in supplier market shares.

## 2. Dataset

**Source:** CEPII — BACI International Trade Database  
**Website:** https://www.cepii.fr/CEPII/en/bdd_modele/bdd_modele_item.asp?id=37  
**Classification:** HS17 (Harmonized System 2017)  
**Years:** 2017–2024  
**Format:** CSV

### Required Files

Download the BACI HS17 annual trade CSV files for 2017–2024, together with the country-code and product-code lookup files.

Place the extracted files in:

`data/raw/BACI_HS17/`

The required filenames are:

- `BACI_HS17_Y2017_V202601.csv` through `BACI_HS17_Y2024_V202601.csv`
- `country_codes_V202601.csv`
- `product_codes_HS17_V202601.csv`

The raw dataset is excluded from Git because of its large size.

### Main Dataset Fields

| Field | Description |
|---|---|
| `t` | Trade year |
| `i` | Exporter country code |
| `j` | Importer country code |
| `k` | HS17 six-digit product code |
| `v` | Trade value (thousands of USD) |
| `q` | Quantity (metric tons, where available) |

**Source-data grain:** One trade record per year, exporter, importer, and HS17 product.

**Business key:** (`t`, `i`, `j`, `k`).

## 3. Lakehouse Architecture

### Bronze Layer

Stores the original BACI records with their source fields preserved as strings.

Additional metadata includes:

- `source_name`
- `ingested_at`
- `load_id`

The Bronze layer also records source-file ingestion counts in `bronze.load_log`.

**Total Bronze records:** 89,207,221.

### Silver Layer

Filters the raw data to Qatar imports (`j = 634`) and applies data-quality checks.

Validation includes year range, country codes, product-code format, trade values, quantities, and duplicate business keys.

Invalid records are directed to a quarantine table. Missing quantities are retained as NULL so valid trade values are not discarded.

**Silver results:**

| Metric | Count |
|---|---:|
| Qatar Bronze records | 467,811 |
| Valid Silver records | 467,811 |
| Quarantined records | 0 |
| Duplicate business keys | 0 |
| Missing quantities | 11,278 |

### Gold Layer

Organizes the cleaned data into a star schema with one fact table and three dimension tables.

| Table | Purpose |
|---|---|
| `gold.fact_imports` | Qatar import values and quantities |
| `gold.dim_year` | Trade years |
| `gold.dim_exporter` | Exporter countries |
| `gold.dim_product` | HS17 product descriptions |

**Fact-table grain:** One row per year, exporter country, and HS17 product imported into Qatar.

All dimension keys were checked for uniqueness and non-null values. Fact-table foreign-key references and business-key uniqueness were also validated.

See `diagrams/star_schema.png` for the schema diagram.

## 4. Environment Setup

Use Python and install the dependencies listed in `requirements.txt`.

From the `assign1` directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## 5. Pipeline Execution

After downloading the required dataset files, run the scripts in this order:

```bash
python setup/00_setup.py
python setup/00_01_bronze_schema.py
python setup/00_02_silver_schema.py
python setup/00_03_gold_schema.py

python pipeline/01_bronze.py
python pipeline/02_silver.py
python pipeline/03_gold.py
```

The Bronze pipeline skips files already recorded in its load log. The Silver and Gold pipelines rebuild their outputs so they can be rerun without accumulating duplicate records.

## 6. Data Analysis

Run the analysis script:

```bash
python analysis/questions.py
```

The analysis answers four questions using Gold tables only:

1. How did Qatar's total import value change from 2017 to 2024?
2. Which ten countries supplied Qatar with the highest import value?
3. Which ten HS17 products accounted for the highest import value?
4. How did the top five suppliers' shares of Qatar's annual imports change?

Four visualizations are produced and saved in `analysis/figures/`.

The executed Jupyter notebook is located at:

`notebooks/lakehouse_pipeline.ipynb`

It includes layer summaries, SQL query results, charts, interpretations, and the star-schema diagram.

## 7. Homework Structure

```text
assign1/
├── analysis/
│   ├── questions.py
│   └── figures/
├── data/
│   └── raw/
│       └── BACI_HS17/
├── diagrams/
│   ├── create_diagram.py
│   └── star_schema.png
├── lakehouse/
├── notebooks/
│   └── lakehouse_pipeline.ipynb
├── pipeline/
│   ├── 01_bronze.py
│   ├── 02_silver.py
│   └── 03_gold.py
├── setup/
│   ├── 00_setup.py
│   ├── 00_01_bronze_schema.py
│   ├── 00_02_silver_schema.py
│   └── 00_03_gold_schema.py
├── .gitignore
├── requirements.txt
└── README.md
```

## 8. Reproducibility Notes

The dataset files and generated lakehouse storage are excluded from version control.

To reproduce the results, download the specified BACI HS17 files, install the Python dependencies, execute the setup and pipeline scripts in order, and run the analysis script or Jupyter notebook.

The pipeline uses relative paths based on the homework directory so it can be executed from a different computer after the required data files are placed in the expected directory.

## 9. Dataset Attribution

CEPII BACI International Trade Database, HS17 classification, 2017–2024.

Source: https://www.cepii.fr/CEPII/en/bdd_modele/bdd_modele_item.asp?id=37

## 10. Known Limitations

The analysis focuses on Qatar's merchandise imports from 2017 to 2024 using the CEPII BACI HS17 dataset. Trade values are reported in current US dollars and are not adjusted for inflation, so changes in import value may reflect both price changes and changes in trade activity.

Some trade records have missing quantities. These records are retained when their trade values are valid, which means quantity-based analysis may be incomplete.

The dataset is based on annual trade records rather than real-time transactions. Additionally, a missing supplier-year observation should not automatically be interpreted as zero trade. For example, no UAE supplier-year observation was found for 2017 in the Gold dataset.

## 11. AI Assistance Acknowledgment

ChatGPT was used as a supporting tool during the development of this homework, including assistance with Python and SQL code, debugging, documentation, and explanations of the Bronze–Silver–Gold architecture. The homework was executed, tested, and reviewed by the student, who is responsible for the final implementation, results, and submitted work.