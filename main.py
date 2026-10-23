
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "KaggleV2-May-2016.csv"
BRONZE_DIR = BASE_DIR / "bronze"
SILVER_DIR = BASE_DIR / "silver"
GOLD_DIR = BASE_DIR / "gold"
OUTPUT_DIR = BASE_DIR / "output"

def main():
    for folder in [BRONZE_DIR, SILVER_DIR, GOLD_DIR, OUTPUT_DIR]:
        folder.mkdir(parents=True, exist_ok=True)

    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_FILE}")

    print("Reading dataset...")
    df = pd.read_csv(DATA_FILE)

    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns)}")
    print("\nColumn names:")
    print(df.columns.tolist())

    print("\nFirst 5 rows:")
    print(df.head())

    # Bronze: preserve a copy of the original data
    df.to_csv(BRONZE_DIR / "appointments_raw.csv", index=False)

    print("\nBronze layer created successfully!")

if __name__ == "__main__":
    main()
