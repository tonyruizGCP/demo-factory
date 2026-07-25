import json
import argparse

def seed_mock_data(dry_run: bool = True):
    mock_data = [
        {"alert_id": "ALT-9002", "severity": "CRITICAL", "service_name": "checkout-payment-service", "error_message": "Database pool exhausted"},
        {"alert_id": "ALT-1001", "severity": "WARNING", "service_name": "user-preference-service", "error_message": "Cache miss ratio high"}
    ]
    if dry_run:
        with open("mock_sre_logs.json", "w") as f:
            json.dump(mock_data, f, indent=2)
        print("[SUCCESS] Mock SRE logs seeded to mock_sre_logs.json (Dry-Run Mode)")
    else:
        print("[GCP MODE] Provisioning BigQuery dataset 'sre_logs_dataset'...")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=True)
    args = parser.parse_args()
    seed_mock_data(args.dry_run)
