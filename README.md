# 🛍️ Retail AI Agent

A **multi-agent conversational AI system** for retail shopping, built with LangGraph, RAG (Qdrant + sentence-transformers), Groq LLM inference, and a Next.js storefront. Seven specialised AI agents—orchestrated by a LangGraph state machine—handle product discovery, inventory checks, loyalty discounts, payment processing, fulfillment scheduling, and post-purchase support, all through a single chat interface powered by an AI assistant named **Aria**.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        NEXT.JS FRONTEND                         │
│         Landing Page · Chat (Aria) · Products · Orders          │
└──────────────────────────────┬───────────────────────────────────┘
                               │  POST /chat (axios)
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                        FASTAPI BACKEND                          │
│                                                                  │
│   ┌───────────────────────────────────────────────────────┐      │
│   │              LangGraph StateGraph (9 nodes)           │      │
│   │                                                       │      │
│   │   Intent Detection ──▸ Route by Intent                │      │
│   │         │                                             │      │
│   │   ┌─────┼──────────┬──────────┬──────────┐            │      │
│   │   ▼     ▼          ▼          ▼          ▼            │      │
│   │  Reco  Inventory  Checkout   Post-     Greeting/     │      │
│   │  Agent  Agent     Chain:     Purchase  Fallback      │      │
│   │  (RAG)            Loyalty→   Agent                   │      │
│   │                   Payment→                           │      │
│   │                   Fulfillment                        │      │
│   └───────────────────────────────────────────────────────┘      │
│                                                                  │
│   ┌────────────────────┐    ┌──────────────────────┐             │
│   │   RAG Pipeline     │    │   Session Manager    │             │
│   │ sentence-transformers│    │   (Upstash Redis)   │             │
│   │ + Qdrant Cloud     │    │   24h TTL, cross-    │             │
│   │ (3 collections)    │    │   channel continuity │             │
│   └────────────────────┘    └──────────────────────┘             │
└──────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **LLM Inference** | Groq (Llama 3.1 8B) | Sub-200ms intent detection, greeting generation, and recommendation synthesis |
| **Agent Orchestration** | LangGraph 0.2 | StateGraph with conditional routing across 9 nodes |
| **Vector Database** | Qdrant Cloud | Semantic search over products, customer history, and promotions (3 collections) |
| **Embeddings** | sentence-transformers (all-MiniLM-L6-v2) | 384-dim vectors for product descriptions and queries |
| **Session Storage** | Upstash Redis | Serverless Redis with REST API; 24h TTL; cross-channel session persistence |
| **Backend** | FastAPI + uvicorn | Async API with auto-generated OpenAPI docs |
| **Frontend** | Next.js 16 + Framer Motion | App Router, TypeScript, TailwindCSS, smooth micro-animations |
| **Containerisation** | Docker | Single-stage `python:3.11-slim` image for Railway deployment |

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- API keys for: [Groq](https://console.groq.com), [Qdrant Cloud](https://cloud.qdrant.io), [Upstash Redis](https://upstash.com)

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your actual API keys

# Start server
python main.py
# → http://localhost:8000  (API docs at /docs)
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.local.example .env.local
# Edit .env.local with your backend URL

# Start dev server
npm run dev
# → http://localhost:3000
```

### Environment Variables

See [`backend/.env.example`](backend/.env.example) for all required variables:

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Groq API key for LLM inference |
| `QDRANT_URL` | Qdrant Cloud cluster URL |
| `QDRANT_API_KEY` | Qdrant Cloud API key |
| `UPSTASH_REDIS_REST_URL` | Upstash Redis REST URL |
| `UPSTASH_REDIS_REST_TOKEN` | Upstash Redis REST token |
| `FRONTEND_URL` | Frontend URL for CORS (default: `http://localhost:3000`) |
| `BACKEND_API_URL` | Backend URL used by agents for self-calls (default: `http://localhost:8000`) |
| `ENVIRONMENT` | `development` or `production` |
| `PORT` | Server port (default: `8000`) |

---

## Project Status

**Deployment-ready.** Live demo available on request. See [`PROJECT_DEEP_DIVE.md`](PROJECT_DEEP_DIVE.md) for full technical documentation covering architecture decisions, the agent self-calling pattern, CORS configuration, RAG pipeline, challenges faced, and future improvements.

---

## Project Structure

```
retail-ai-agent/
├── backend/
│   ├── agents/               # 7 specialised AI agents
│   │   ├── sales_agent.py          # Intent detection
│   │   ├── recommendation_agent.py # RAG-based product discovery
│   │   ├── inventory_agent.py      # Stock checking
│   │   ├── loyalty_agent.py        # Discount calculation
│   │   ├── payment_agent.py        # Payment processing
│   │   ├── fulfillment_agent.py    # Delivery scheduling
│   │   └── post_purchase_agent.py  # Tracking, returns, feedback
│   ├── graph/                # LangGraph orchestration
│   │   ├── state.py                # AgentState TypedDict (20+ fields)
│   │   └── agent_graph.py          # 9-node StateGraph with routing
│   ├── rag/                  # RAG pipeline
│   │   ├── embedder.py             # Text embedding (MiniLM-L6-v2)
│   │   ├── indexer.py              # Startup data indexing
│   │   └── vectorstore.py          # Qdrant CRUD operations
│   ├── session/              # Session management
│   │   └── session_manager.py      # Redis CRUD with 24h TTL
│   ├── api/                  # FastAPI routes + middleware
│   ├── data/                 # JSON data (products, customers, inventory, promotions)
│   ├── main.py               # FastAPI app entrypoint
│   └── Dockerfile
├── frontend/
│   ├── app/                  # Next.js App Router pages
│   │   ├── page.tsx                # Landing page
│   │   ├── chat/page.tsx           # Chat interface (Aria)
│   │   ├── products/page.tsx       # Product discovery
│   │   └── orders/page.tsx         # Order tracking
│   └── lib/api.ts            # API client (axios)
└── PROJECT_DEEP_DIVE.md      # Full technical documentation
```
