
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "silver" / "appointments_clean.csv"
GOLD_DIR = BASE_DIR / "gold"

def summarize(df, group_column):
    result = df.groupby(group_column, dropna=False).agg(
        appointments=("appointmentid", "count"),
        missed=("no_show", lambda s: (s == "Yes").sum()),
        attended=("no_show", lambda s: (s == "No").sum())
    ).reset_index()
    result["no_show_rate_percent"] = (
        result["missed"] / result["appointments"] * 100
    ).round(2)
    return result

def main():
    GOLD_DIR.mkdir(parents=True, exist_ok=True)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Clean dataset not found: {INPUT_FILE}. Run clean_data.py first."
        )

    df = pd.read_csv(INPUT_FILE)
    df["appointmentday"] = pd.to_datetime(
        df["appointmentday"], errors="coerce", utc=True
    )
    df["scheduledday"] = pd.to_datetime(
        df["scheduledday"], errors="coerce", utc=True
    )

    total = len(df)
    missed = int((df["no_show"] == "Yes").sum())
    attended = int((df["no_show"] == "No").sum())

    kpis = pd.DataFrame({
        "metric": [
            "total_appointments",
            "unique_patients",
            "appointments_attended",
            "appointments_missed",
            "no_show_rate_percent"
        ],
        "value": [
            total,
            df["patientid"].nunique(),
            attended,
            missed,
            round(missed / total * 100, 2) if total else 0
        ]
    })
    kpis.to_csv(GOLD_DIR / "overall_kpis.csv", index=False)

    summarize(df, "gender").to_csv(
        GOLD_DIR / "gender_summary.csv", index=False
    )
    summarize(df, "neighbourhood").sort_values(
        "no_show_rate_percent", ascending=False
    ).to_csv(GOLD_DIR / "neighbourhood_summary.csv", index=False)
    summarize(df, "sms_received").to_csv(
        GOLD_DIR / "sms_summary.csv", index=False
    )

    df["appointment_month"] = df["appointmentday"].dt.strftime("%Y-%m")
    summarize(df, "appointment_month").sort_values(
        "appointment_month"
    ).to_csv(GOLD_DIR / "monthly_summary.csv", index=False)

    df["waiting_days"] = (
        df["appointmentday"].dt.normalize()
        - df["scheduledday"].dt.normalize()
    ).dt.days

    summarize(df, "waiting_days").sort_values(
        "waiting_days"
    ).to_csv(GOLD_DIR / "waiting_time_summary.csv", index=False)

    print("Gold analytics completed successfully!")
    print(f"Total appointments: {total:,}")
    print(f"Unique patients: {df['patientid'].nunique():,}")
    print(f"Attended: {attended:,}")
    print(f"Missed: {missed:,}")
    print(f"No-show rate: {missed / total * 100:.2f}%" if total else "No-show rate: 0%")
    print(f"Gold files saved to: {GOLD_DIR}")

if __name__ == "__main__":
    main()
