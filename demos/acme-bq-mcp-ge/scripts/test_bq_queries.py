#!/usr/bin/env python3
"""
Acme BigQuery Query Benchmark & Test Suite
Executes live analytical SQL queries against the Acme media intelligence dataset
and displays benchmark timing and tabular outputs.
"""

import os
import sys
import time
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "truiz-agy-demo")
BQ_DATASET_ID = os.getenv("BQ_DATASET_ID", "acme_media_intelligence")
BQ_LOCATION = os.getenv("BQ_LOCATION", "US")

print(f"🚀 Initializing BigQuery Client (Project: {GCP_PROJECT_ID}, Dataset: {BQ_DATASET_ID})...\n")
client = bigquery.Client(project=GCP_PROJECT_ID, location=BQ_LOCATION)

QUERIES = [
    {
        "name": "1. Brand Share of Voice & Weighted Sentiment (Last 30 Days)",
        "sql": f"""
        SELECT 
            brand_name, 
            COUNT(mention_id) as total_mentions,
            ROUND(AVG(sentiment_score), 3) as avg_sentiment,
            SUM(reach) as total_reach,
            SUM(engagement_count) as total_engagements
        FROM `{GCP_PROJECT_ID}.{BQ_DATASET_ID}.media_mentions`
        WHERE published_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
        GROUP BY brand_name
        ORDER BY total_mentions DESC
        """
    },
    {
        "name": "2. Cross-Channel Performance & Negative Sentiment Spikes",
        "sql": f"""
        SELECT 
            source_type,
            COUNT(mention_id) as mention_count,
            COUNTIF(sentiment_label = 'negative') as negative_mentions,
            ROUND(100.0 * COUNTIF(sentiment_label = 'negative') / COUNT(*), 2) as negative_percentage,
            ROUND(AVG(reach), 0) as avg_reach_per_post
        FROM `{GCP_PROJECT_ID}.{BQ_DATASET_ID}.media_mentions`
        GROUP BY source_type
        ORDER BY negative_percentage DESC
        """
    },
    {
        "name": "3. Marketing Campaign Impact vs Target Impressions",
        "sql": f"""
        SELECT 
            c.brand_name,
            c.campaign_name,
            c.status,
            c.target_reach,
            c.actual_reach,
            ROUND(100.0 * c.actual_reach / c.target_reach, 1) as pct_target_achieved,
            c.sentiment_uplift
        FROM `{GCP_PROJECT_ID}.{BQ_DATASET_ID}.campaign_performance` c
        ORDER BY pct_target_achieved DESC
        """
    },
    {
        "name": "4. 90-Day Rolling Daily Sentiment Trends (Acme Corp vs Peers)",
        "sql": f"""
        WITH daily_stats AS (
            SELECT 
                date,
                brand_name,
                total_mentions,
                avg_sentiment,
                AVG(avg_sentiment) OVER(
                    PARTITION BY brand_name 
                    ORDER BY date 
                    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                ) as rolling_7d_sentiment
            FROM `{GCP_PROJECT_ID}.{BQ_DATASET_ID}.daily_sentiment_aggregates`
        )
        SELECT * FROM daily_stats
        WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 14 DAY)
        ORDER BY date DESC, brand_name ASC
        LIMIT 10
        """
    }
]

def format_table(headers, rows):
    if not rows:
        return "(No rows returned)"
    col_widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(val)))
    
    header_line = " | ".join(str(h).ljust(col_widths[i]) for i, h in enumerate(headers))
    sep_line = "-+-".join("-" * col_widths[i] for i in range(len(headers)))
    row_lines = [" | ".join(str(val).ljust(col_widths[i]) for i, val in enumerate(row)) for row in rows]
    return "\n".join([header_line, sep_line] + row_lines)

def run_tests():
    total_start = time.time()
    for q in QUERIES:
        print("=" * 80)
        print(f"📊 {q['name']}")
        print("=" * 80)
        print(f"SQL Snippet:\n{q['sql'].strip()}\n")
        
        start_time = time.time()
        try:
            query_job = client.query(q['sql'])
            results = query_job.result()
            duration = time.time() - start_time
            
            headers = [field.name for field in results.schema]
            rows = [[str(val) for val in row.values()] for row in results]
            
            print(format_table(headers, rows))
            print(f"\n⚡ Execution Time: {duration:.3f}s | Bytes Processed: {query_job.total_bytes_processed or 0:,} bytes\n")
        except Exception as e:
            print(f"❌ Query Execution Failed: {e}\n")

    print("=" * 80)
    print(f"🎉 All queries executed in {time.time() - total_start:.2f}s total.")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()
