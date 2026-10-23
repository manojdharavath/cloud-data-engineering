
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
BRONZE_FILE = BASE_DIR / "bronze" / "appointments_raw.csv"
SILVER_DIR = BASE_DIR / "silver"
OUTPUT_DIR = BASE_DIR / "output"

def main():
    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(BRONZE_FILE)
    original_count = len(df)

    # Normalize column names
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace("-", "_", regex=False)
        .str.replace(" ", "_", regex=False)
    )

    # Convert dates and numeric columns
    for col in ["scheduledday", "appointmentday"]:
        df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)

    for col in [
        "age", "scholarship", "hipertension", "diabetes",
        "alcoholism", "handcap", "sms_received"
    ]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Track every reason a record is rejected
    reasons = pd.Series("", index=df.index, dtype="object")

    def reject(mask, reason):
        mask = mask.fillna(True) if hasattr(mask, "fillna") else mask
        reasons.loc[mask] = reasons.loc[mask].apply(
            lambda old: f"{old}; {reason}" if old else reason
        )

    # Missing required fields
    required = [
        "patientid", "appointmentid", "gender",
        "scheduledday", "appointmentday", "age",
        "neighbourhood", "no_show"
    ]
    for col in required:
        reject(df[col].isna(), f"missing_{col}")

    # Invalid values
    reject(df["age"] < 0, "negative_age")
    reject(df["age"] > 120, "age_over_120")
    reject(df["gender"].notna() & ~df["gender"].isin(["F", "M"]), "invalid_gender")
    reject(df["no_show"].notna() & ~df["no_show"].isin(["Yes", "No"]), "invalid_no_show")

    for col in ["scholarship", "hipertension", "diabetes", "alcoholism", "sms_received"]:
        reject(~df[col].isin([0, 1]), f"invalid_{col}")

    reject(~df["handcap"].isin([0, 1, 2, 3, 4]), "invalid_handcap")
    reject(
        df["appointmentday"].notna()
        & df["scheduledday"].notna()
        & (df["appointmentday"].dt.date < df["scheduledday"].dt.date),
        "appointment_before_booking"
    )

    # AppointmentID should be unique
    reject(df["appointmentid"].duplicated(keep="first"), "duplicate_appointment_id")

    df["rejection_reason"] = reasons
    rejected = df[df["rejection_reason"] != ""].copy()
    clean = df[df["rejection_reason"] == ""].drop(columns=["rejection_reason"]).copy()

    # Calculate waiting days for analysis
    clean["waiting_days"] = (
        clean["appointmentday"].dt.normalize()
        - clean["scheduledday"].dt.normalize()
    ).dt.days

    clean.to_csv(SILVER_DIR / "appointments_clean.csv", index=False)
    rejected.to_csv(SILVER_DIR / "appointments_rejected.csv", index=False)

    report = pd.DataFrame({
        "metric": [
            "input_records", "valid_records", "rejected_records",
            "duplicate_appointment_ids"
        ],
        "value": [
            original_count, len(clean), len(rejected),
            int(df["appointmentid"].duplicated().sum())
        ]
    })
    report.to_csv(OUTPUT_DIR / "data_quality_report.csv", index=False)

    print("Silver layer completed!")
    print(f"Input records: {original_count:,}")
    print(f"Valid records: {len(clean):,}")
    print(f"Rejected records: {len(rejected):,}")
    print(f"Quality report: {OUTPUT_DIR / 'data_quality_report.csv'}")

if __name__ == "__main__":
    main()
