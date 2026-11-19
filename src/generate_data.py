"""
Generate synthetic data for the Pharma Sales Data Management project.

Creates:
  data/master/hospital_master.csv   - clean hospital master (like a reference/master data source)
  data/master/product_master.csv    - clean product master
  data/raw/<distributor>/<YYYY-MM>.csv - messy monthly sales files from 3 distributors

Each distributor file has its own column names and date format, and contains
realistic data-quality problems for you to find and fix in later modules.

All names are fictional. Run:  python src/generate_data.py
"""

import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

SEED = 42                      # fixed seed -> same data every run (reproducible)
MONTHS = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]
ROWS_PER_FILE = 400

ROOT = Path(__file__).resolve().parents[1]
MASTER_DIR = ROOT / "data" / "master"
RAW_DIR = ROOT / "data" / "raw"

rng = random.Random(SEED)

# ---------------------------------------------------------------------------
# 1. Master data (the "truth" we will match against)
# ---------------------------------------------------------------------------
PREFECTURES = {
    "Tokyo": ["Shinjuku", "Minato", "Setagaya", "Shibuya", "Chuo"],
    "Kanagawa": ["Yokohama", "Kawasaki", "Sagamihara"],
    "Osaka": ["Osaka", "Sakai", "Toyonaka"],
    "Aichi": ["Nagoya", "Toyota", "Okazaki"],
    "Fukuoka": ["Fukuoka", "Kitakyushu"],
    "Hokkaido": ["Sapporo", "Asahikawa"],
}
NAME_STYLES = ["{city} Central Hospital", "{city} General Hospital", "{city} University Hospital",
               "{city} Medical Center", "{city} Red Cross Hospital", "{city} Memorial Clinic",
               "{city} Cancer Center", "{city} Municipal Hospital"]
HOSPITAL_TYPES = {"University Hospital": "University", "Cancer Center": "Specialist",
                  "Clinic": "Clinic", "Municipal": "Public", "Red Cross": "Public"}


def hospital_type(name: str) -> str:
    for key, value in HOSPITAL_TYPES.items():
        if key in name:
            return value
    return "General"


hospitals = []
for pref, cities in PREFECTURES.items():
    for city in cities:
        for style in rng.sample(NAME_STYLES, k=4):
            name = style.format(city=city)
            hospitals.append({
                "hospital_id": f"H{len(hospitals) + 1:04d}",
                "hospital_name": name,
                "prefecture": pref,
                "city": city,
                "hospital_type": hospital_type(name),
                "bed_count": rng.choice([19, 50, 120, 200, 350, 500, 800, 1100]),
            })
hospital_master = pd.DataFrame(hospitals)

products = [
    ("ONC-101", "Onconix 80mg Capsule", "Oncology - Hematology", 3200),
    ("ONC-102", "Onconix 160mg Capsule", "Oncology - Hematology", 6100),
    ("ONC-201", "Immunoval 100mg Injection", "Oncology - Solid Tumor", 98000),
    ("ONC-202", "Immunoval 200mg Injection", "Oncology - Solid Tumor", 189000),
    ("ONC-301", "Cyclotab 50mg Tablet", "Oncology - Solid Tumor", 2700),
    ("SUP-401", "Antiemetic Support 8mg Tablet", "Supportive Care", 450),
    ("SUP-402", "Neutro-Boost 3.6mg Syringe", "Supportive Care", 41000),
]
product_master = pd.DataFrame(products, columns=["product_code", "product_name",
                                                 "therapeutic_area", "list_price_jpy"])

# ---------------------------------------------------------------------------
# 2. Ways a hospital name gets "messed up" in distributor files
# ---------------------------------------------------------------------------
ABBREVIATIONS = {"Hospital": ["Hosp.", "Hosp", "HP"], "University": ["Univ.", "Univ"],
                 "Medical Center": ["Med. Ctr", "Medical Ctr."], "General": ["Gen."],
                 "Central": ["Ctrl", "Cent."], "Municipal": ["Muni."]}


def messy_name(name: str) -> str:
    """Return a realistic variant of a clean hospital name."""
    r = rng.random()
    if r < 0.45:
        return name                                   # clean
    if r < 0.60:
        return name.upper()                           # ALL CAPS
    if r < 0.72:
        return "  " + name.replace(" ", "  ", 1) + " "  # extra spaces
    if r < 0.88:                                      # abbreviation
        for full, shorts in ABBREVIATIONS.items():
            if full in name:
                return name.replace(full, rng.choice(shorts))
        return name
    # small typo: swap two letters
    i = rng.randrange(1, len(name) - 2)
    return name[:i] + name[i + 1] + name[i] + name[i + 2:]


# ---------------------------------------------------------------------------
# 3. Distributor profiles: different columns + date formats
# ---------------------------------------------------------------------------
DISTRIBUTORS = {
    "alpha_medical": {
        "columns": {"date": "InvoiceDate", "hospital": "CustomerName", "product": "ItemCode",
                    "qty": "Qty", "amount": "NetAmountJPY"},
        "date_format": "%Y-%m-%d",
    },
    "kanto_pharma": {
        "columns": {"date": "SALES_DT", "hospital": "SHIP_TO_NAME", "product": "PRODUCT_CD",
                    "qty": "UNITS", "amount": "SALES_AMT"},
        "date_format": "%d/%m/%Y",
    },
    "sakura_medlink": {
        "columns": {"date": "Transaction Date", "hospital": "Facility", "product": "SKU",
                    "qty": "Quantity", "amount": "Amount (JPY)"},
        "date_format": "%Y/%m/%d",
    },
}


def random_day(month: str) -> date:
    year, mon = map(int, month.split("-"))
    start = date(year, mon, 1)
    return start + timedelta(days=rng.randrange(0, 28))


def build_file(month: str, profile: dict) -> pd.DataFrame:
    cols = profile["columns"]
    rows = []
    for _ in range(ROWS_PER_FILE):
        hosp = hospital_master.sample(1, random_state=rng.randrange(10**9)).iloc[0]
        prod = product_master.sample(1, random_state=rng.randrange(10**9)).iloc[0]
        qty = rng.choice([1, 1, 2, 2, 3, 5, 10, 20])
        discount = rng.uniform(0.85, 0.98)            # distributors sell below list price
        amount = round(qty * prod.list_price_jpy * discount)

        row = {
            cols["date"]: random_day(month).strftime(profile["date_format"]),
            cols["hospital"]: messy_name(hosp.hospital_name),
            cols["product"]: prod.product_code,
            cols["qty"]: qty,
            cols["amount"]: amount,
        }

        # ---- inject data-quality problems ----
        p = rng.random()
        if p < 0.02:
            row[cols["product"]] = ""                                  # missing product code
        elif p < 0.035:
            row[cols["qty"]] = -row[cols["qty"]]                       # return (negative qty)
            row[cols["amount"]] = -row[cols["amount"]]
        elif p < 0.045:
            row[cols["hospital"]] = rng.choice(["Unknown Clinic", "Nakano Private Clinic",
                                                "Test Customer"])      # not in master
        elif p < 0.05:
            row[cols["date"]] = "2026-02-30"                           # invalid date
        elif p < 0.055:
            row[cols["product"]] = row[cols["product"]].lower().replace("-", "")  # bad format
        rows.append(row)

    df = pd.DataFrame(rows)
    dupes = df.sample(frac=0.03, random_state=rng.randrange(10**9))   # ~3% exact duplicates
    return pd.concat([df, dupes]).sample(frac=1, random_state=rng.randrange(10**9))


def main() -> None:
    MASTER_DIR.mkdir(parents=True, exist_ok=True)
    hospital_master.to_csv(MASTER_DIR / "hospital_master.csv", index=False)
    product_master.to_csv(MASTER_DIR / "product_master.csv", index=False)

    total = 0
    for dist, profile in DISTRIBUTORS.items():
        out_dir = RAW_DIR / dist
        out_dir.mkdir(parents=True, exist_ok=True)
        for month in MONTHS:
            df = build_file(month, profile)
            df.to_csv(out_dir / f"{month}.csv", index=False, encoding="utf-8")
            total += len(df)

    print(f"Hospitals: {len(hospital_master)} | Products: {len(product_master)}")
    print(f"Distributor files: {len(DISTRIBUTORS) * len(MONTHS)} | Sales rows: {total}")
    print(f"Written to: {ROOT / 'data'}")


if __name__ == "__main__":
    main()
