# Managed Agents API - Unified Commerce Agent Fullstack Demo

A complete, end-to-end fullstack web application and interactive control room built with **FastAPI**, **Vanilla HTML/CSS/JS**, and the **Managed Agents API on Gemini Enterprise Agent Platform**, designed specifically to showcase [OmniCommerce](https://omnicommerce.com/) how they can bring AI agents to their mid-market e-commerce merchants.

---

## 🎯 OmniCommerce Value Proposition

OmniCommerce's competitive advantage lies in bridging **Marketing Cloud**, **Commerce Cloud**, and **Service Cloud**. This demo showcases **Omni-AI**—an enterprise agent that operates seamlessly across all three pillars:

1. **Commerce Cloud (Inventory & Product Intelligence)**
   - Autonomous SKU catalog search and inventory availability checks.
   - Intelligent scarcity notifications (*"Warning: Only 3 units remaining!"*).

2. **Marketing Cloud (eRFM Omnichannel Automation)**
   - Leverages **eRFM** (Recency, Frequency, Monetary Value) customer profiles.
   - Generates hyper-personalized abandoned cart emails and companion SMS copy for VIP vs. At-Risk customer tiers.

3. **Service Cloud (Autonomous Support & Frictionless Handoff)**
   - Real-time order tracking and shipment issue resolution.
   - Deflects tier-1 support tickets while offering recovery vouchers.
   - Automatically formats structured JSON tickets and triggers live-agent escalation protocols for high-value refund requests.

---

## 🏗️ Fullstack Application Architecture

```
managed-agents-ecommerce/
├── app.py                                   # FastAPI Backend (REST & SSE Stream Server)
├── requirements.txt                         # Python Dependencies
├── .env.example                             # Environment Variables Template
├── .env                                     # GCP Project & GCS Skill Bucket Config (Git-ignored)
├── README.md                                # CE Presentation Guide & Architecture
├── unified_commerce_skill.md       # Remote GCS Skill Playbook Directive
├── managed_agents_ecommerce.ipynb  # Interactive Colab / Jupyter Notebook alternative
├── static/                                  # Web UI Frontend Assets
│   ├── index.html                           # Control Room Single-Page App Skeleton
│   ├── style.css                            # Modern Slate & Indigo Dark Theme Stylesheet
│   └── main.js                              # Tab Switching, SSE Stream Decoder & API Logic
└── merchant_data/                           # Mock Merchant Database (JSON Storage)
    ├── catalog.json                         # SKU Specs & Stock Counts
    ├── orders.json                          # Fulfillment History & Carrier Tracking
    ├── customers.json                       # eRFM Segments & Abandoned Carts
    └── tickets.json                         # Open Support Tickets & Escalation Logs
```

---

## 🚀 Quickstart & Setup Guide

### 1. Prerequisites & Requirements
- Python 3.10+
- Active Google Cloud credentials (`gcloud auth application-default login`) with access to project `truiz-agent-builder`.

### 2. Environment Configuration
Copy `.env.example` to create your local `.env` file:

```bash
cp .env.example .env
```

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `GCP_PROJECT` | Google Cloud Project ID for Vertex AI & Managed Agents API | `truiz-agent-builder` |
| `GOOGLE_CLOUD_LOCATION` | GCP location endpoint for Managed Agents Control Plane | `global` |
| `SKILL_GCS_BUCKET` | GCS Bucket storing remote skill playbooks & merchant datasets | `truiz-agent-builder-managed-agents` |

### 3. Local App Startup
Run the server locally using Python:

```bash
cd /usr/local/google/home/tonyruiz/Desktop/demos/jetski/demos/demo-factory/demos/managed-agents-ecommerce
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

Once running, navigate to **[http://localhost:8005](http://localhost:8005)** in your web browser!

---

## 💡 Customer Pitch & Live Demo Script

When presenting to OmniCommerce leadership or technical teams, open the web app control room and click through the three preset demo trigger chips:

### Scenario 1: Commerce Cloud (Inventory Scarcity)
- **Trigger Button:** 📦 *Stock Scarcity Check*
- **Prompt:** *"Check inventory for 'UltraBoost Performance Running Shoes' in size 10 and warn me if stock is low!"*
- **What happens:** Omni-AI inspects `merchant_data/catalog.json`, identifies that only 3 units remain in stock, and generates an urgency-driven notification for the merchant.

### Scenario 2: Marketing Cloud (eRFM Cart Recovery)
- **Trigger Button:** ✉️ *VIP Cart Recovery*
- **Prompt:** *"Draft an abandoned-cart recovery email and a companion SMS for Gold VIP customer Sarah Jenkins who left a leather duffel bag in her cart."*
- **What happens:** Omni-AI retrieves Sarah's eRFM profile from `customers.json` (Recency: 5 days, 14 orders, $3,450 spend), notes her Gold VIP status, and drafts an exclusive VIP recovery offer with SMS fallback.

### Scenario 3: Service Cloud (Frictionless Escalation)
- **Trigger Button:** 🆘 *Support Escalation*
- **Prompt:** *"My order #90210 has been delayed for 2 weeks. This is unacceptable, I want a refund!"*
- **What happens:** Omni-AI retrieves order `#90210` from `orders.json`, detects shipment delay with FedEx, apologizes with a `$15` recovery code (`CARE15`), and outputs a structured JSON escalation ticket for Service Cloud human queue.

---

## 🔑 Key CE Talking Points for OmniCommerce Executive Meetings

1. **Unlocking Unified Data:** Merchants hate context switching between marketing tools, storefronts, and helpdesks. Managed Agents API allows a single agent container to read storefront data and write directly to marketing campaigns.
2. **Instant Ticket Deflection:** Up to 60% of common tier-1 support queries (order status, returns) are handled automatically, saving merchants thousands in support costs while improving customer satisfaction.
3. **Turnkey Skill Deployment:** OmniCommerce can author standard skill playbooks once in GCS and deploy them across thousands of mid-market merchants in seconds.

---

## 🛠️ Challenges Encountered & Platform Workarounds

During the development and testing of this Managed Agents API demo, we identified several platform nuances and implemented production-grade workarounds:

| Challenge | Root Cause | Workaround / Solution |
| :--- | :--- | :--- |
| **1. SDK Client Signature** | `google.genai.Client(enterprise=True)` raises `TypeError` in `google-genai>=2.0.0`. | Use `google.genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)`. For maximum stability, use direct REST API calls (`https://aiplatform.googleapis.com/v1beta1/...`) with OAuth2 Bearer Tokens. |
| **2. Resource Provisioning Delay (`HTTP 400`)** | Newly deployed agents or container sandboxes return `400 BadRequestError: Resource setup has just started. Please try again shortly.` during initial warming. | Implemented automatic retry loop in `app.py` `sse_generator()`. Retries 6 times (waiting 4s between attempts) while streaming a status update: `*[Initializing container environment sandbox... please wait]*`. |
| **3. Stream Decoding Mismatch (`step.delta`)** | Managed Agents REST stream emits `event_type: "step.delta"` (with `delta.type == "text"` or `arguments_delta`) instead of standard Gemini `content.delta`. | Updated SSE parser in `app.py` to match `step.delta` events and extract `text` chunks and `arguments_delta` code traces. |
| **4. GCS Source Container Mounts** | GCS source mounts with relative target `./skills` or `./` didn't place subdirectories in `/workspace`, causing `merchant_data/catalog.json` to be missing. | Uploaded structured GCS paths (`gs://{bucket}/merchant_data/` and `gs://{bucket}/skills/`) and configured explicit GCS target mappings (`target: "merchant_data"` and `target: "skills"`). |
| **5. Port Contention** | Default uvicorn port `8000` conflicted with sibling demo servers (`[Errno 98]`). | Assigned dedicated port `8005` in `app.py` and implemented automated process cleanup scripts. |

