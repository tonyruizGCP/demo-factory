import json
from typing import Dict, Any

MOCK_SRE_LOGS = [
    {
        "timestamp": "2026-07-25T22:30:00Z",
        "service_name": "checkout-payment-service",
        "severity": "CRITICAL",
        "log_message": "Fatal: Database connection pool exhausted. 504 gateway timeout",
        "trace_id": "tr-99812401"
    },
    {
        "timestamp": "2026-07-25T22:29:55Z",
        "service_name": "db-proxy-service",
        "severity": "ERROR",
        "log_message": "Max connections (100/100) reached for database pool payment_db",
        "trace_id": "tr-99812400"
    }
]

def get_simulated_bigquery_logs(service_name: str) -> Dict[str, Any]:
    filtered = [l for l in MOCK_SRE_LOGS if l["service_name"] == service_name]
    if not filtered:
        filtered = MOCK_SRE_LOGS
    return {
        "status": "success",
        "query_executed": f"SELECT * FROM `{service_name}` WHERE severity IN ('ERROR', 'CRITICAL')",
        "records_retrieved": len(filtered),
        "logs": filtered
    }
