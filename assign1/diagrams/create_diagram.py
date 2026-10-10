
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUTPUT_DIR = Path(__file__).resolve().parent

fig, ax = plt.subplots(figsize=(12, 7))
ax.set_xlim(0, 12)
ax.set_ylim(0, 7)
ax.axis("off")

def draw_table(x, y, w, h, title, fields):
    rect = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.08",
        linewidth=1.5,
        edgecolor="black",
        facecolor="white"
    )
    ax.add_patch(rect)

    ax.text(
        x + w / 2, y + h - 0.35,
        title,
        ha="center",
        va="center",
        fontsize=12,
        fontweight="bold"
    )

    ax.plot(
        [x, x + w],
        [y + h - 0.65, y + h - 0.65],
        color="black"
    )

    for index, field in enumerate(fields):
        ax.text(
            x + 0.2,
            y + h - 1.0 - index * 0.35,
            field,
            fontsize=10,
            va="center"
        )

draw_table(
    4.4, 4.4, 3.2, 2.3,
    "fact_imports",
    [
        "year_key (FK)",
        "exporter_key (FK)",
        "product_key (FK)",
        "trade_value",
        "quantity"
    ]
)

draw_table(
    0.3, 0.6, 3.1, 1.8,
    "dim_year",
    ["year_key (PK)", "year"]
)

draw_table(
    4.45, 0.6, 3.1, 2.1,
    "dim_exporter",
    ["exporter_key (PK)", "country_name", "country_iso3"]
)

draw_table(
    8.6, 0.6, 3.1, 1.8,
    "dim_product",
    ["product_key (PK)", "product_description"]
)

# Relationships
ax.plot([5.0, 1.85], [4.4, 2.4], color="black", linewidth=1.5)
ax.plot([6.0, 6.0], [4.4, 2.7], color="black", linewidth=1.5)
ax.plot([7.0, 10.15], [4.4, 2.4], color="black", linewidth=1.5)

ax.set_title(
    "Qatar Imports Gold Layer — Star Schema",
    fontsize=16,
    fontweight="bold",
    pad=20
)

plt.savefig(
    OUTPUT_DIR / "star_schema.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close()
print("Star-schema diagram saved successfully!")
