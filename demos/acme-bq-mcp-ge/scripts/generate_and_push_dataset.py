#!/usr/bin/env python3
"""
Acme BigQuery Dataset Generator & Provisioner
Generates realistic media intelligence, brand mentions, and sentiment telemetry,
then provisions and loads the tables in a Google Cloud BigQuery project.
"""

import os
import sys
import uuid
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any

from dotenv import load_dotenv
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

# Load environment variables
load_dotenv()

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "truiz-agy-demo")
BQ_DATASET_ID = os.getenv("BQ_DATASET_ID", "acme_media_intelligence")
BQ_LOCATION = os.getenv("BQ_LOCATION", "US")

if not GCP_PROJECT_ID or GCP_PROJECT_ID == "your-gcp-project-id":
    print("❌ Error: Please set GCP_PROJECT_ID in your .env file or environment.")
    sys.exit(1)

print(f"🚀 Initializing BigQuery Client for Project: {GCP_PROJECT_ID}, Region: {BQ_LOCATION}")
client = bigquery.Client(project=GCP_PROJECT_ID, location=BQ_LOCATION)

# ----------------------------------------------------------------------
# 1. Ensure Dataset Exists
# ----------------------------------------------------------------------
dataset_ref = bigquery.DatasetReference(GCP_PROJECT_ID, BQ_DATASET_ID)

try:
    dataset = client.get_dataset(dataset_ref)
    print(f"✅ Found existing dataset: {GCP_PROJECT_ID}.{BQ_DATASET_ID}")
except NotFound:
    print(f"📦 Creating BigQuery dataset: {GCP_PROJECT_ID}.{BQ_DATASET_ID}...")
    dataset = bigquery.Dataset(dataset_ref)
    dataset.location = BQ_LOCATION
    dataset.description = "Acme Corp Media Intelligence & Enterprise Analytics for Gemini Enterprise MCP Demo"
    dataset.labels = {"customer": "acme", "workload": "mcp_demo", "managed_by": "ce_team"}
    dataset = client.create_dataset(dataset, timeout=30)
    print(f"✅ Created dataset: {dataset.dataset_id}")

# ----------------------------------------------------------------------
# 2. Schema Definitions
# ----------------------------------------------------------------------
SCHEMAS = {
    "media_mentions": [
        bigquery.SchemaField("mention_id", "STRING", mode="REQUIRED", description="Unique identifier for media mention"),
        bigquery.SchemaField("published_at", "TIMESTAMP", mode="REQUIRED", description="Timestamp when article or post was published"),
        bigquery.SchemaField("brand_name", "STRING", mode="REQUIRED", description="Tracked brand mentioned in the content"),
        bigquery.SchemaField("source_type", "STRING", mode="NULLABLE", description="Source category: news, broadcast, blog, reddit, twitter, podcast"),
        bigquery.SchemaField("source_name", "STRING", mode="NULLABLE", description="Publication or domain name (e.g. Wall Street Journal, TechCrunch)"),
        bigquery.SchemaField("title", "STRING", mode="NULLABLE", description="Headline or post title"),
        bigquery.SchemaField("excerpt", "STRING", mode="NULLABLE", description="Content excerpt containing brand keyword"),
        bigquery.SchemaField("language", "STRING", mode="NULLABLE", description="ISO language code (e.g. en, es, fr, de, ja)"),
        bigquery.SchemaField("country", "STRING", mode="NULLABLE", description="Country of publication (e.g. US, UK, DE, JP)"),
        bigquery.SchemaField("sentiment_score", "FLOAT64", mode="NULLABLE", description="Normalized sentiment score from -1.0 to 1.0"),
        bigquery.SchemaField("sentiment_label", "STRING", mode="NULLABLE", description="Categorical sentiment: POSITIVE, NEUTRAL, NEGATIVE"),
        bigquery.SchemaField("reach", "INT64", mode="NULLABLE", description="Estimated audience reach of the publication"),
        bigquery.SchemaField("engagement_count", "INT64", mode="NULLABLE", description="Total social shares, comments, or likes"),
        bigquery.SchemaField("topics", "STRING", mode="REPEATED", description="Identified topical tags (e.g. AI, Cloud, Earnings, ESG)"),
        bigquery.SchemaField("url", "STRING", mode="NULLABLE", description="Canonical URL to the original article or mention")
    ],
    "brand_competitors": [
        bigquery.SchemaField("brand_name", "STRING", mode="REQUIRED", description="Primary brand name"),
        bigquery.SchemaField("competitor_name", "STRING", mode="REQUIRED", description="Tracked industry competitor"),
        bigquery.SchemaField("industry_vertical", "STRING", mode="NULLABLE", description="Market category (e.g. Enterprise Cloud, Generative AI, Cyber)"),
        bigquery.SchemaField("market_cap_tier", "STRING", mode="NULLABLE", description="MegaCap, LargeCap, MidCap, Startup")
    ],
    "campaign_performance": [
        bigquery.SchemaField("campaign_id", "STRING", mode="REQUIRED", description="Unique campaign ID"),
        bigquery.SchemaField("brand_name", "STRING", mode="REQUIRED", description="Brand running the campaign"),
        bigquery.SchemaField("campaign_name", "STRING", mode="REQUIRED", description="Marketing or PR campaign title"),
        bigquery.SchemaField("start_date", "DATE", mode="REQUIRED", description="Campaign launch date"),
        bigquery.SchemaField("end_date", "DATE", mode="NULLABLE", description="Campaign end date"),
        bigquery.SchemaField("target_reach", "INT64", mode="NULLABLE", description="Target audience impressions"),
        bigquery.SchemaField("actual_reach", "INT64", mode="NULLABLE", description="Actual recorded reach across media channels"),
        bigquery.SchemaField("sentiment_uplift", "FLOAT64", mode="NULLABLE", description="Net sentiment change during campaign window"),
        bigquery.SchemaField("status", "STRING", mode="NULLABLE", description="ACTIVE, COMPLETED, PLANNED")
    ],
    "daily_sentiment_aggregates": [
        bigquery.SchemaField("date", "DATE", mode="REQUIRED", description="Aggregation calendar date"),
        bigquery.SchemaField("brand_name", "STRING", mode="REQUIRED", description="Brand name"),
        bigquery.SchemaField("total_mentions", "INT64", mode="NULLABLE", description="Daily volume count"),
        bigquery.SchemaField("positive_mentions", "INT64", mode="NULLABLE", description="Count of positive mentions"),
        bigquery.SchemaField("negative_mentions", "INT64", mode="NULLABLE", description="Count of negative mentions"),
        bigquery.SchemaField("neutral_mentions", "INT64", mode="NULLABLE", description="Count of neutral mentions"),
        bigquery.SchemaField("avg_sentiment", "FLOAT64", mode="NULLABLE", description="Weighted average sentiment score"),
        bigquery.SchemaField("total_reach", "INT64", mode="NULLABLE", description="Total combined audience reach")
    ]
}

# ----------------------------------------------------------------------
# 3. Data Generation
# ----------------------------------------------------------------------
BRANDS = ["Acme Corp", "AcmeCloud", "NovaAI", "DataPulse", "StreamCore", "CyberShield"]
SOURCES = [
    ("news", "Reuters", 0.95),
    ("news", "Bloomberg", 0.95),
    ("news", "Wall Street Journal", 0.92),
    ("news", "TechCrunch", 0.85),
    ("news", "VentureBeat", 0.80),
    ("broadcast", "CNBC Morning Call", 0.88),
    ("broadcast", "Bloomberg Tech TV", 0.86),
    ("reddit", "r/MachineLearning", 0.70),
    ("reddit", "r/CloudComputing", 0.65),
    ("twitter", "Twitter/X Tech Sphere", 0.75),
    ("podcast", "All-In Podcast", 0.82),
    ("podcast", "Latent Space Podcast", 0.78),
    ("blog", "Hacker News Discussions", 0.72)
]
TOPICS_POOL = ["Enterprise AI", "Cloud Infrastructure", "Security & Governance", "LLM Evals", "BigQuery MCP", "Agentic Workflows", "Q3 Earnings", "Customer Churn"]

def generate_mock_data():
    random.seed(42)
    now = datetime.utcnow()
    
    # 1. Media Mentions
    mentions = []
    for _ in range(1500):
        brand = random.choice(BRANDS)
        src_type, src_name, cred_multiplier = random.choice(SOURCES)
        pub_time = now - timedelta(days=random.randint(0, 89), hours=random.randint(0, 23), minutes=random.randint(0, 59))
        
        base_sentiment = random.uniform(-0.6, 0.9)
        if brand in ["Acme Corp", "AcmeCloud", "NovaAI"]:
            base_sentiment += 0.15
        
        sentiment_score = round(max(-1.0, min(1.0, base_sentiment)), 3)
        if sentiment_score > 0.15:
            sentiment_label = "positive"
        elif sentiment_score < -0.15:
            sentiment_label = "negative"
        else:
            sentiment_label = "neutral"

        reach = int(random.randint(5000, 2500000) * cred_multiplier)
        engagements = int(reach * random.uniform(0.005, 0.08))
        topics = random.sample(TOPICS_POOL, k=random.randint(1, 3))
        
        mentions.append({
            "mention_id": str(uuid.uuid4()),
            "published_at": pub_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "brand_name": brand,
            "source_type": src_type,
            "source_name": src_name,
            "title": f"{brand} expands {topics[0]} capabilities across enterprise scale",
            "excerpt": f"Analysts highlight {brand}'s continuous leadership in {topics[0]} and next-generation solutions.",
            "language": "en",
            "country": random.choice(["US", "UK", "DE", "FR", "JP", "AU"]),
            "sentiment_score": sentiment_score,
            "sentiment_label": sentiment_label,
            "reach": reach,
            "engagement_count": engagements,
            "topics": topics,
            "url": f"https://www.{src_name.lower().replace(' ', '')}.com/articles/{str(uuid.uuid4())[:8]}"
        })
        
    # 2. Competitors Mapping
    competitors = [
        {"brand_name": "Acme Corp", "competitor_name": "MegaCorp AI", "industry_vertical": "Enterprise AI", "market_cap_tier": "MegaCap"},
        {"brand_name": "Acme Corp", "competitor_name": "Apex Data", "industry_vertical": "Enterprise AI", "market_cap_tier": "LargeCap"},
        {"brand_name": "AcmeCloud", "competitor_name": "CloudNova", "industry_vertical": "Cloud Infrastructure", "market_cap_tier": "LargeCap"},
        {"brand_name": "AcmeCloud", "competitor_name": "SkyScale", "industry_vertical": "Cloud Infrastructure", "market_cap_tier": "LargeCap"},
        {"brand_name": "NovaAI", "competitor_name": "Acme Corp", "industry_vertical": "Generative AI", "market_cap_tier": "LargeCap"},
        {"brand_name": "DataPulse", "competitor_name": "AcmeCloud", "industry_vertical": "Data Analytics", "market_cap_tier": "MidCap"},
        {"brand_name": "CyberShield", "competitor_name": "ZeroTrust Core", "industry_vertical": "Security & Governance", "market_cap_tier": "LargeCap"}
    ]
    
    # 3. Campaign Performance
    campaigns = [
        {
            "campaign_id": "CMP-2026-ACME-01",
            "brand_name": "Acme Corp",
            "campaign_name": "Acme AI Enterprise Platform Launch",
            "start_date": (now - timedelta(days=45)).strftime("%Y-%m-%d"),
            "end_date": (now - timedelta(days=5)).strftime("%Y-%m-%d"),
            "target_reach": 15000000,
            "actual_reach": 18450000,
            "sentiment_uplift": 0.28,
            "status": "COMPLETED"
        },
        {
            "campaign_id": "CMP-2026-ACME-02",
            "brand_name": "AcmeCloud",
            "campaign_name": "Autonomous Agent Gateway Awareness",
            "start_date": (now - timedelta(days=20)).strftime("%Y-%m-%d"),
            "end_date": (now + timedelta(days=10)).strftime("%Y-%m-%d"),
            "target_reach": 8000000,
            "actual_reach": 9200000,
            "sentiment_uplift": 0.19,
            "status": "ACTIVE"
        },
        {
            "campaign_id": "CMP-2026-NOV-01",
            "brand_name": "NovaAI",
            "campaign_name": "Multimodal Horizon Global Summit",
            "start_date": (now - timedelta(days=60)).strftime("%Y-%m-%d"),
            "end_date": (now - timedelta(days=30)).strftime("%Y-%m-%d"),
            "target_reach": 20000000,
            "actual_reach": 24100000,
            "sentiment_uplift": 0.35,
            "status": "COMPLETED"
        }
    ]
    
    # 4. Daily Sentiment Aggregates (last 90 days)
    daily_aggregates = []
    for brand in BRANDS:
        for d in range(90):
            day_date = (now - timedelta(days=d)).date()
            pos = random.randint(10, 65)
            neg = random.randint(2, 18)
            neu = random.randint(15, 45)
            total = pos + neg + neu
            avg_s = round((pos * 0.7 + neu * 0.0 - neg * 0.6) / total, 3)
            tot_reach = random.randint(150000, 3500000)
            
            daily_aggregates.append({
                "date": day_date.strftime("%Y-%m-%d"),
                "brand_name": brand,
                "total_mentions": total,
                "positive_mentions": pos,
                "negative_mentions": neg,
                "neutral_mentions": neu,
                "avg_sentiment": avg_s,
                "total_reach": tot_reach
            })

    return {
        "media_mentions": mentions,
        "brand_competitors": competitors,
        "campaign_performance": campaigns,
        "daily_sentiment_aggregates": daily_aggregates
    }

# ----------------------------------------------------------------------
# 4. Table Creation & Ingestion
# ----------------------------------------------------------------------
def provision_tables(data_dict: Dict[str, List[Dict[str, Any]]]):
    for table_name, schema in SCHEMAS.items():
        table_ref = dataset_ref.table(table_name)
        rows = data_dict[table_name]
        
        # Configure Table definition
        table = bigquery.Table(table_ref, schema=schema)
        
        # Partitioning & Clustering for optimal performance
        if table_name == "media_mentions":
            table.time_partitioning = bigquery.TimePartitioning(
                type_=bigquery.TimePartitioningType.DAY,
                field="published_at"
            )
            table.clustering_fields = ["brand_name", "source_type"]
        elif table_name == "daily_sentiment_aggregates":
            table.time_partitioning = bigquery.TimePartitioning(
                type_=bigquery.TimePartitioningType.DAY,
                field="date"
            )
            table.clustering_fields = ["brand_name"]
            
        try:
            client.delete_table(table_ref, not_found_ok=True)
            table = client.create_table(table)
            print(f"📦 Created table: {table.full_table_id}")
        except Exception as e:
            print(f"⚠️ Error creating table {table_name}: {e}")
            continue
            
        # Insert rows using LoadJob for high throughput
        job_config = bigquery.LoadJobConfig(
            schema=schema,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
        )
        
        print(f"⏳ Loading {len(rows)} records into `{table_name}`...")
        load_job = client.load_table_from_json(rows, table_ref, job_config=job_config)
        load_job.result() # Wait for job to complete
        print(f"✅ Successfully loaded {load_job.output_rows} rows into `{table_name}`.\n")

if __name__ == "__main__":
    print("=" * 70)
    print(" Acme BigQuery Media Intelligence Demo Generator")
    print("=" * 70)
    mock_data = generate_mock_data()
    provision_tables(mock_data)
    print("🎉 Dataset provisioning and seeding complete!")
