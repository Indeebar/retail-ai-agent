# Retail AI Agent — Project Deep-Dive

## 1. Problem Statement

Modern retail—especially fashion—suffers from a discovery problem: customers browse hundreds of products, get overwhelmed, and either buy the wrong thing or abandon the cart entirely. Traditional e-commerce search uses keyword matching, which fails for intent-rich queries like *"I need something for a friend's sangeet, budget around ₹3,500, something flowy."*

**What this system solves:**

This project is a **multi-agent AI shopping assistant** named **Aria** that handles the full post-discovery retail loop—from natural-language product search and personalised recommendations through inventory checks, loyalty discounts, payment processing, fulfillment scheduling, and post-purchase support—all inside a single conversational interface.

Instead of navigating menus, the user talks to Aria. Aria understands intent, retrieves semantically relevant products from a vector database, applies loyalty perks, processes payments, and schedules delivery—spanning 7 specialised agents coordinated by a LangGraph state machine.

---

## 2. Architecture Overview

### 2.1 High-Level Flow

```
User Message
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│                    NEXT.JS FRONTEND                     │
│  Landing Page · Chat Interface · Products · Orders      │
│                         │                               │
│                POST /chat (axios)                       │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│                  FASTAPI BACKEND                        │
│                                                         │
│  ┌──────────────┐     ┌────────────────────────────┐    │
│  │  Chat Route  │────▸│    LangGraph StateGraph    │    │
│  └──────────────┘     │                            │    │
│         │             │  ┌────────────────────┐    │    │
│         │             │  │ Intent Detection   │    │    │
│  ┌──────▼──────┐      │  └────────┬───────────┘    │    │
│  │   Session   │      │           │                │    │
│  │  Manager    │      │   ┌───────▼────────┐       │    │
│  │  (Redis)    │      │   │  Route by      │       │    │
│  └─────────────┘      │   │  Intent        │       │    │
│                       │   └───────┬────────┘       │    │
│                       │     ┌─────┼─────┐          │    │
│                       │     ▼     ▼     ▼          │    │
│                       │  ┌─────┬─────┬──────────┐  │    │
│                       │  │Reco │Inv. │Checkout  │  │    │
│                       │  │     │     │Chain:    │  │    │
│                       │  │     │     │Loyalty→  │  │    │
│                       │  │     │     │Payment→  │  │    │
│                       │  │     │     │Fulfill.  │  │    │
│                       │  ├─────┼─────┼──────────┤  │    │
│                       │  │Greet│Post │Fallback  │  │    │
│                       │  │     │Purch│          │  │    │
│                       │  └─────┴─────┴──────────┘  │    │
│                       └────────────────────────────┘    │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │              RAG Pipeline                        │   │
│  │  Sentence-Transformers (all-MiniLM-L6-v2)       │   │
│  │           ↕                                      │   │
│  │  Qdrant Cloud (3 collections:                    │   │
│  │    products, customer_history, promotions)       │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Multi-Agent Design

The system employs **7 specialised agents**, each a self-contained Python module with a single `run(input: dict) -> dict` interface:

| Agent | Responsibility | Key Behaviour |
|---|---|---|
| **Sales Agent** | Intent detection and classification | Uses Groq LLM to classify user messages into one of 8 intents |
| **Recommendation Agent** | RAG-based product discovery | Queries Qdrant for semantically similar products, filters by purchase history, calls Groq for natural-language response |
| **Inventory Agent** | Real-time stock checking | Self-calls backend `/inventory` API via `httpx` to check stock by SKU and location |
| **Loyalty Agent** | Discount and perks calculation | Self-calls `/loyalty` API to fetch tier-based discounts and coupon eligibility |
| **Payment Agent** | Payment processing with retry | Self-calls `/payment` API with exponential backoff and idempotency keys |
| **Fulfillment Agent** | Delivery/pickup scheduling | Self-calls `/fulfillment` API to schedule shipping and generate tracking IDs |
| **Post-Purchase Agent** | Tracking, returns, feedback | Handles order tracking queries, return initiation, and feedback collection |

### 2.3 Agent Communication via LangGraph

Agents don't call each other directly. Instead, all coordination flows through a **LangGraph StateGraph**:

1. Every user message enters the `intent_detection` node.
2. A `route_by_intent` conditional edge dispatches to the appropriate worker node.
3. Each worker node runs its corresponding agent's `.run()` method and writes results back into the shared `AgentState`.
4. For checkout, a **sequential chain** is enforced: `loyalty_node → payment_node → fulfillment_node → END`.
5. All other nodes go directly to `END`.

The `AgentState` TypedDict (20+ fields) carries everything: session identity, conversation history, cart contents, agent outputs, payment/fulfillment status, and the final response.

### 2.4 RAG Pipeline Flow

```
User Query: "Show me ethnic wear for a wedding under ₹4000"
    │
    ▼
┌─────────────────────────────────────────┐
│  1. Embed query with all-MiniLM-L6-v2  │
│     (384-dimensional vector)            │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│  2. Semantic search in Qdrant Cloud    │
│     • products collection (top-5)      │
│     • customer_history (top-3)         │
│     • promotions (top-3)               │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│  3. Filter out already-purchased items │
│     using customer purchase history    │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│  4. Build context prompt with          │
│     retrieved products + promotions    │
│     + customer preferences             │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│  5. Groq LLM (llama-3.1-8b-instant)   │
│     generates natural-language         │
│     recommendation with product names, │
│     prices, and occasion suitability   │
└─────────────────────────────────────────┘
```

**Indexing** happens at server startup. The `run_indexer()` function is idempotent—it checks `collection_has_data()` and skips re-indexing if data already exists. Three collections are maintained:
- **products** — 28 SKUs with rich descriptions (fabric, occasion, body type)
- **customer_history** — 12 customer profiles with purchase histories and preferences
- **promotions** — Coupons, seasonal campaigns, and bundle deals (flattened into a single collection)

---

## 3. Tech Stack with Justifications

| Technology | Role | Why This Choice |
|---|---|---|
| **FastAPI** | Backend API framework | Async-native, automatic OpenAPI docs, Pydantic validation. Perfect for an LLM-powered backend where every agent call is `async`. |
| **LangGraph** | Agent orchestration | Provides declarative state machines with conditional routing. Avoids the "chain-of-calls" anti-pattern where agents call each other in spaghetti fashion. The graph is inspectable and testable. |
| **Groq** | LLM inference | Sub-200ms inference on Llama 3.1 8B. For a conversational retail agent, latency matters more than model size—Groq's speed makes multi-turn conversations feel responsive. |
| **Qdrant Cloud** | Vector database | Managed cloud service with free tier. Supports cosine similarity, payload filtering, and collection-level isolation. Zero-ops compared to self-hosting Pinecone or Weaviate. |
| **sentence-transformers** | Text embedding | `all-MiniLM-L6-v2` produces 384-dim vectors with excellent quality for product descriptions. Runs locally (no API calls for embedding), keeping indexing costs at zero. |
| **Upstash Redis** | Session storage | Serverless Redis with REST API. Sessions expire after 24h (TTL). Supports the cross-channel continuity feature—start on web, continue on mobile, same conversation. |
| **Next.js 16** | Frontend framework | React Server Components, App Router, excellent TypeScript support. Vercel deployment is zero-config. |
| **Framer Motion** | UI animations | Smooth micro-animations for the landing page, product cards, and chat transitions make the UI feel premium without heavy custom CSS. |
| **Docker** | Containerisation | Single `Dockerfile` for consistent Railway deployment. `python:3.11-slim` base keeps image lean. |
| **httpx** | Internal HTTP calls | Async HTTP client used by agents to self-call backend APIs. Chosen over `requests` for async compatibility with FastAPI's event loop. |

---

## 4. The Agent Self-Calling Pattern

### The Pattern

Four agents (inventory, loyalty, payment, fulfillment) call *their own backend's API endpoints* instead of importing business logic directly:

```python
# In inventory_agent.py
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")

async with httpx.AsyncClient(base_url=BACKEND_API_URL, timeout=10.0) as client:
    response = await client.get(f"/inventory/{sku_id}")
```

### Why It Works

1. **Separation of concerns**: Agents are pure "decision-makers" that compose API calls. The API routes contain the data-access logic. Neither layer knows about the other's internals.

2. **Testability**: Each agent can be tested in isolation by mocking the HTTP layer. Each API route can be tested independently via `curl` or `pytest`.

3. **Consistency**: Every data access (whether from agents, frontend, or external systems) goes through the same validated API endpoints. No backdoor imports.

### Why It Works in Railway (Production)

In Railway, the backend is a single container. When an agent inside the container calls `http://localhost:8000/inventory/SKU_001`, it's making a request to *itself*—loopback networking inside the same container. This is:
- **Fast**: No network hop, sub-millisecond latency.
- **Reliable**: No DNS resolution, no TLS overhead.
- **Simple**: `BACKEND_API_URL` defaults to `http://localhost:8000`, which works both locally and in production without any configuration change.

The `localhost` fallback means this pattern works out of the box in any single-container deployment (Railway, Render, Fly.io) without environment variable changes.

---

## 5. CORS Configuration Decisions

### Current Configuration

```python
allowed_origins = [
    "http://localhost:3000",       # Local frontend dev
    "http://localhost:3001",       # Alternate local port
    "https://*.vercel.app",        # All Vercel preview deployments
]
# Plus: FRONTEND_URL from environment (for exact production URL)
```

### Design Decisions

| Decision | Rationale |
|---|---|
| **Wildcard `*.vercel.app`** | Every Vercel push creates a unique preview URL (`https://retail-ai-agent-abc123.vercel.app`). Without the wildcard, you'd need to add each preview URL manually. Starlette ≥ 0.27.0 supports wildcard subdomain matching natively. |
| **`FRONTEND_URL` env var** | The exact production Vercel URL is set as an environment variable in Railway. This is the most restrictive origin and should be the primary allowed origin in production. |
| **`allow_credentials=True`** | Required for session cookies and Authorization headers in cross-origin requests. The frontend sends `session_id` in request bodies (not cookies), so this is a precaution for future auth integration. |
| **`allow_methods=["*"]` and `allow_headers=["*"]`** | Permissive for development speed. In a production hardening pass, these would be locked down to `["GET", "POST"]` and `["Content-Type", "Authorization"]`. |

### Tradeoff

The wildcard `*.vercel.app` is technically broader than needed—it allows *any* Vercel app to make requests. In production, the `FRONTEND_URL` environment variable provides the exact-match restriction. The wildcard is a convenience for preview deployments during development and is acceptable given that the API has no destructive write operations beyond mock payment processing.

---

## 6. LLM-as-Judge Evaluation Framework

### How It Works

The evaluation framework uses a **second LLM call** to assess the quality of the primary agent's response. This is implemented as a structured prompt that asks the judge model to rate responses on specific criteria:

### What It Measures

| Dimension | Description |
|---|---|
| **Relevance** | Does the response address the user's actual query? Did the agent correctly interpret the intent? |
| **Factual Grounding** | Are recommended products real SKUs from the data? Are prices accurate? Are inventory claims verifiable? |
| **Completeness** | Did the agent provide all information the user would need? (e.g., price, availability, occasion suitability) |
| **Tone & Persona** | Does Aria maintain a warm, professional tone consistent with a premium fashion consultant? |
| **Context Retention** | In multi-turn conversations, does the agent reference earlier messages appropriately? |

### Implementation Approach

Each agent's `run()` method returns structured output. The evaluation framework:
1. Takes the user query + agent response + retrieved context.
2. Passes them to Groq with a structured evaluation prompt.
3. Returns scores (1-5) per dimension + a free-text justification.
4. The scores are logged and can be aggregated for overall system health monitoring.

This approach was chosen over traditional metrics (BLEU, ROUGE) because retail conversations require subjective quality assessment—a response can be factually correct but tonally wrong, or complete but irrelevant.

---

## 7. Key Challenges and Resolutions

### Challenge 1: Agent-to-Agent Communication Without Spaghetti

**Problem**: With 7 agents, naively wiring them creates O(n²) potential call paths. The checkout flow alone requires 3 agents to execute sequentially.

**Resolution**: LangGraph's `StateGraph` provides a clean DAG structure. Agents never import each other—they read from and write to the shared `AgentState`. The graph enforces execution order through edges. The conditional `route_by_intent` function is the single routing decision point.

### Challenge 2: Conversation State Across Channels

**Problem**: A customer starts shopping on web, switches to mobile, continues on kiosk. The conversation must persist seamlessly.

**Resolution**: The entire `AgentState` (20+ fields) is serialised as JSON and stored in Upstash Redis with a 24-hour TTL. The `switch_channel` endpoint updates only the `channel` field while preserving all other state. The frontend reads `session_id` from `localStorage` and sends it in every request.

### Challenge 3: RAG Indexing on Cold Start

**Problem**: Qdrant collections need to be populated before the first request can be served. First startup downloads a 90MB sentence-transformers model.

**Resolution**: The `run_indexer()` function is called during FastAPI's `on_startup` event. It's idempotent—`collection_has_data()` checks if at least 1 point exists before re-indexing. The indexer never deletes existing data (`ensure_collections_exist` only creates missing collections). First Railway deployment takes 5-8 minutes; subsequent deploys skip indexing entirely.

### Challenge 4: Windows Development + Unicode Emoji in LLM Responses

**Problem**: Python's default `cp1252` encoding on Windows crashes when Groq returns responses containing emoji characters.

**Resolution**: Added `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` at entry points. The `"replace"` error handler ensures the process never crashes on encoding issues—unprintable characters are replaced with `�` instead.

### Challenge 5: Payment Reliability

**Problem**: Mock payment processing needs to simulate real-world failure modes (network timeouts, insufficient funds) while still being deterministic for testing.

**Resolution**: The payment agent includes exponential backoff retry logic and generates idempotency keys per transaction. The mock `/payment` endpoint returns probabilistic success/failure based on amount thresholds, allowing the retry mechanism to be exercised during testing.

---

## 8. What I Would Do Differently / Next Version

### Architecture Improvements

- **Streaming responses**: Currently the entire graph executes before returning. Next version would use Server-Sent Events (SSE) to stream Aria's response token-by-token, dramatically improving perceived latency.
- **Parallel agent execution**: The recommendation node could run concurrently with inventory checks using LangGraph's branching. Currently all paths are sequential.
- **Tool-calling agent**: Replace the `route_by_intent → fixed node` pattern with a ReAct-style tool-calling agent that can invoke multiple tools per turn. This eliminates the rigid intent taxonomy.

### Data & ML Improvements

- **Fine-tuned embedding model**: `all-MiniLM-L6-v2` is a general-purpose model. A model fine-tuned on fashion product descriptions would improve retrieval relevance.
- **Hybrid search**: Combine vector similarity with BM25 keyword matching for better recall on exact product names and SKU IDs.
- **Real user feedback loop**: Log every interaction, let users thumbs-up/down responses, and use that signal to refine prompts.

### Production Hardening

- **Rate limiting**: Add per-IP and per-session rate limiting (currently absent).
- **Auth layer**: JWT-based authentication instead of passing `customer_id` in the request body.
- **Observability**: Integrate LangSmith or Langfuse for LLM call tracing, token usage tracking, and latency monitoring.
- **CORS lockdown**: Replace `allow_methods=["*"]` with explicit `["GET", "POST"]`.
- **CI pipeline**: Add GitHub Actions with `pytest` for agent unit tests and a Playwright E2E test suite.

### Feature Additions

- **Image search**: Let users upload a photo ("find me something like this") using CLIP embeddings.
- **Multi-language support**: Hindi + English code-switching is extremely common in Indian retail.
- **Voice input**: Integrate Whisper for voice-to-text in the chat interface.
- **Admin dashboard**: Analytics on popular queries, conversion rates, and agent performance metrics.
