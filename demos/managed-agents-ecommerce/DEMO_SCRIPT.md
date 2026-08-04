# Customer Demo & Presentation Script: Unified Commerce Agent ("Omni-AI")

**Presenter:** Tony Ruiz, Google Cloud Customer Engineer (AI)  
**Target Audience:** OmniCommerce Executive Leadership (CTO, VP of Product, Chief Revenue Officer, Lead Engineers)  
**Goal:** Demonstrate how Google Cloud's Managed Agents API empowers OmniCommerce to embed an enterprise-grade AI assistant into their platform, bridging Commerce, Marketing, and Service Clouds for mid-market merchants.

---

## 📋 Presentation Overview & Agenda (30-Minute Meeting)

| Time | Segment | Focus Area |
|---|---|---|
| **00:00 - 05:00** | **Executive Briefing** | The Mid-Market Merchant Dilemma: Siloed Commerce, Marketing & Support |
| **05:00 - 10:00** | **Architecture & Concept** | How Managed Agents API powers OmniCommerce's "Omni-AI" |
| **10:00 - 22:00** | **Live Product Demo** | Live Acts: Commerce Cloud, Marketing Cloud, Service Cloud |
| **22:00 - 27:00** | **Q&A & Technical Deep-Dive** | Security, GCS Skill Mounting, Container Isolation & Scalability |
| **27:00 - 30:00** | **Next Steps & PoC Proposal** | 2-Week Pilot Framework for OmniCommerce Engineering |

---

## 🎤 Act-by-Act Walkthrough Script

### Act 1: Executive Briefing & Opening Hook (5 mins)

**[Speaker / CE (Tony)]:**
> *"Thank you everyone for taking the time today. Mid-market e-commerce merchants ($20M to $200M in GMV) face a massive operational challenge: context switching between three disconnected silos—their storefront inventory, their email/SMS marketing suites, and their helpdesk ticketing systems.*
>
> *OmniCommerce already leads the market by bringing Commerce Cloud, Marketing Cloud, and Service Cloud under one platform. Today, we are going to show you how Google Cloud’s **Managed Agents API on Gemini Enterprise Agent Platform** enables OmniCommerce to launch **Omni-AI**—an intelligent assistant that unifies all three clouds autonomously for your merchants."*

---

### Act 2: Setting up the Command Center (2 mins)

**[Action: Open Web App at `http://localhost:8005` or display `managed_agents_ecommerce.ipynb`]**

**[Speaker / CE (Tony)]:**
> *"What you see here is the OmniCommerce AI Control Room. Notice the top status bar: we are connected live to Google Cloud Vertex AI under project `truiz-agent-builder`.
>
> In the sidebar, we have our three product cloud dashboards alongside **Omni-AI Sandbox**. Behind the scenes, Google Cloud Managed Agents provisions an isolated, remote execution container that mounts OmniCommerce’s merchant dataset—catalogs, customer eRFM segments, order history, and support tickets."*

---

### Act 3: Commerce Cloud — Real-Time Inventory & Stock Scarcity (5 mins)

**[Action: Click on 'Commerce Cloud' tab to show catalog grid, then return to Chat and click trigger 'Stock Scarcity Check']**

**[Prompt Triggered]:**
> *"Check inventory for 'UltraBoost Performance Running Shoes' in size 10 and warn me if stock is low!"*

**[Key Talking Points to Highlight as Stream Renders]:**
1. **Autonomous File System Access:** The agent inspects `merchant_data/catalog.json` inside the remote container.
2. **Business Rule Compliance:** The GCS skill playbook specifies that if stock is $\le 5$ units, Omni-AI must append a high-converting scarcity alert.
3. **Response:**
   > *"UltraBoost Performance Running Shoes (SKU: `UB-RUN-100`) are in stock for Size 10 in Blue. However, **only 3 units remain in warehouse stock**. Recommending immediate checkout notification."*

**[Speaker / CE (Tony)]:**
> *"Notice how Omni-AI didn't just query the database—it applied business logic from a remote GCS skill playbook to drive immediate shopper conversion."*

---

### Act 4: Marketing Cloud — eRFM Omnichannel Cart Recovery (5 mins)

**[Action: Click on 'Marketing Cloud' tab to show Customer Cards, then return to Chat and click trigger 'VIP Cart Recovery']**

**[Prompt Triggered]:**
> *"Draft an abandoned-cart recovery email and a companion SMS for Gold VIP customer Sarah Jenkins who left a leather duffel bag in her cart."*

**[Key Talking Points to Highlight as Stream Renders]:**
1. **eRFM Customer Profiling:** Omni-AI parses `merchant_data/customers.json` and evaluates Sarah's metrics:
   - **Recency:** Purchased 5 days ago
   - **Frequency:** 14 prior orders
   - **Monetary Value:** $3,450 total spend
   - **VIP Status:** Gold Tier
2. **Dynamic Copy Generation:** Generates an exclusive Gold VIP email draft featuring dynamic subject lines, customized perks (e.g. complimentary express shipping), and a companion SMS fallback.
3. **Response:**
   > **Email Subject:** *"Exclusive Perk for Gold VIP Sarah: Your Nomad Duffel is Waiting"*  
   > **SMS Fallback:** *"Hi Sarah! As a Gold VIP, complete your purchase of the Nomad Leather Duffel in 24 hrs for free express shipping: [Link]"*

**[Speaker / CE (Tony)]:**
> *"This bridges Commerce and Marketing seamlessly. Rather than generic abandoned cart templates, OmniCommerce merchants can deliver hyper-personalized omnichannel campaigns based on real-time eRFM data."*

---

### Act 5: Service Cloud — Ticket Deflection & Live Escalation (5 mins)

**[Action: Click on 'Service Cloud' tab to show Orders and Tickets tables, then return to Chat and click trigger 'Support Escalation']**

**[Prompt Triggered]:**
> *"My order #90210 has been delayed for 2 weeks. This is unacceptable, I want a refund!"*

**[Key Talking Points to Highlight as Stream Renders]:**
1. **Shipment Verification:** Omni-AI inspects `orders.json` for order `#90210`, checks carrier tracking (`FedEx TRK987654321`), and confirms delivery was expected on July 10th.
2. **Deflection & Compensation:** Apologizes and automatically issues a `$15` recovery discount code (`CARE15`).
3. **Structured Human Escalation:** Because the customer requested a refund over $150 and expressed high frustration, Omni-AI formats a clean JSON ticket payload and triggers the Service Cloud escalation protocol:
   > `[Escalating to Service Cloud Human Queue]`  
   > `Ticket Payload: {"CustomerEmail": "sarah.jenkins@example.com", "Order_ID": "90210", "Issue_Summary": "Package delayed by 11 days, refund requested", "Urgency": "High"}`

**[Speaker / CE (Tony)]:**
> *"Omni-AI autonomously deflects up to 60% of tier-1 support queries, while ensuring high-risk or high-value cases are escalated to human agents with full context."*

---

## 🙋‍♂️ Q&A & Objection Handling Matrix

| Customer Question / Objection | Recommended CE Response |
|---|---|
| **"How is customer merchant data isolated between different stores?"** | *"Each merchant session spins up a sandboxed, stateful container (`environment_id`) managed by Google Cloud Vertex AI. Storage and memory boundaries are completely isolated at the container level."* |
| **"How hard is it to update business logic across thousands of merchants?"** | *"OmniCommerce can maintain core skill playbooks (Markdown directives) in GCS buckets. Updating a skill in GCS instantly updates agent behavior across all merchant containers without modifying underlying code."* |
| **"Can Omni-AI search live external websites or shipping APIs?"** | *"Yes! Managed Agents API natively supports `google_search` grounding for real-time web lookups and custom tool integration for external REST/gRPC endpoints."* |

---

## 🎯 Next Steps & PoC Proposal

**[Speaker / CE (Tony)]:**
> *"We propose a joint **2-Week Proof-of-Concept (PoC)**:
> 1. **Week 1:** Connect OmniCommerce's sandbox API endpoints to a custom Managed Agent configuration in Google Cloud.
> 2. **Week 2:** Run pilot benchmark testing across 50 simulated merchant workflows.
> 
> Let's schedule a technical discovery session with your engineering team this Thursday to kick off setup!"*
