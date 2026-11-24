# Third Agent

A customer-support assistant for an online shop. It answers questions about shop policies (RAG), looks up a customer's own orders (MCP tool), and opens support tickets only after a human reviewer approves them.

This is a learning project built step by step. It is not production software. See [Known limitations](#known-limitations) for what is missing.

## What it does

A logged-in customer chats with the agent in Persian:

- **"How many days do I have to return an item?"** → the agent searches the shop documents (pgvector) and answers from them.
- **"Where is my order?"** → the agent calls an MCP tool that reads the orders of the logged-in customer only.
- **"My mouse arrived broken, I want to file a complaint."** → the agent drafts a ticket, the conversation **pauses**, a reviewer approves or rejects it through the API, and only then the ticket is written to the database.

## Architecture

```
Customer ──► FastAPI ──► LangGraph agent ──┬─► search_documents ─► pgvector (RAG)
             (JWT login)   (state saved     ├─► get_customer_orders ─► MCP server ─► PostgreSQL
                            in PostgreSQL)  └─► create_ticket ─► [pause for human] ─► PostgreSQL
                                                   ▲
Reviewer ──► /reviews (API key) ───────────────────┘  approve / reject → conversation resumes
```

The agent graph:

```
START ─► guard ──┬─ blocked ─► END
                 └─ ok ─► agent ──┬─ no tool calls ─► END
                           ▲      ├─ safe tool ─► tools ──┐
                           │      └─ create_ticket ─► approval (pause) ─┬─ approved ─► tools
                           │                                            └─ rejected ─┐
                           └─────────────────────────────────────────────────────────┘
```

| Part | Technology |
|---|---|
| Database | PostgreSQL 16 + pgvector (Docker) |
| Migrations | Alembic |
| Embeddings and chat model | OpenRouter (default: `baai/bge-m3`, `mistralai/ministral-14b-2512`) |
| Tools | MCP (stdio server and client) |
| Agent flow, memory, human approval | LangGraph (PostgreSQL checkpointer, `interrupt`) |
| Validation | Pydantic |
| API | FastAPI |
| Tests | pytest |

## Design decisions

- **Identity never comes from the model.** The customer's email is read from a signed JWT by the server and passed to the tools. The `get_customer_orders` and `create_ticket` tools have no email parameter, so even a fully tricked model cannot read another customer's data.
- **Conversations belong to their owner.** The internal conversation id is `<email>::<client id>`, so another customer cannot continue someone else's conversation by guessing the id.
- **Writes need a human.** Reading tools run freely. The only tool that writes data (`create_ticket`) pauses the graph until a reviewer decides. The decision is recorded with an atomic `UPDATE ... WHERE status = 'pending'`, so a request can be decided only once.
- **Plain code where the rule is fixed.** Only the language understanding and the final wording use the model. Everything with a fixed rule (login, ownership, limits, the review queue) is ordinary code.
- **A hand-written agent loop first.** `src/third_agent/agent/loop.py` is the loop written by hand; `graph/agent_graph.py` is the same loop as a LangGraph graph. `graph/support_graph.py` is an earlier fixed-path workflow, kept for comparison.

## Quick start (Docker)

You need Docker Desktop and an [OpenRouter](https://openrouter.ai) API key.

```bash
cp .env.example .env        # then fill in the values (see "Configuration")

docker compose up --build   # starts db → runs migrations → starts the API

# In a second terminal, one-time data setup:
docker compose run --rm api python -m third_agent.database.seed      # sample customers, products, orders
docker compose run --rm api python -m third_agent.rag.ingest         # embed docs/knowledge into pgvector
docker compose run --rm api python scripts/set_passwords.py          # set passwords for the sample customers
```

Open http://127.0.0.1:8000/docs.

1. `POST /login` with `ali@example.com` and the password you set.
2. Click **Authorize** and paste the token (without the word `Bearer`).
3. `POST /chat` with `{"question": "سفارشم کجاست؟"}`. Reuse the returned `thread_id` to continue the conversation.

To try the approval flow, ask for a complaint (for example "ماوسی که خریدم خراب بود، می‌خوام شکایت ثبت کنم"). The answer says the request awaits approval. Then, as the reviewer:

```bash
curl http://127.0.0.1:8000/reviews -H "X-Reviewer-Key: <REVIEWER_API_KEY>"
curl -X POST http://127.0.0.1:8000/reviews/1/decision \
  -H "X-Reviewer-Key: <REVIEWER_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'
```

Stop with `docker compose down`. Do **not** add `-v`: it deletes the database volume.

## Configuration

Copy `.env.example` to `.env`. Never commit `.env`.

| Variable | Meaning |
|---|---|
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Database name and credentials |
| `POSTGRES_HOST`, `POSTGRES_PORT` | Default `localhost` and `5432`. Docker Compose sets the host to `db` for its own services |
| `OPENROUTER_API_KEY` | Key for embeddings and chat |
| `EMBEDDING_MODEL` | Embedding model. The table column is `vector(1024)`, so the model must produce 1024 numbers (default `baai/bge-m3`). Changing to a model with another size needs a new migration and re-ingestion |
| `CHAT_MODEL` | Chat model that supports tool calling |
| `JWT_SECRET` | Secret that signs login tokens. Generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `REVIEWER_API_KEY` | Key for the reviewer endpoints. If empty, the endpoints reject every request |
| `LANGGRAPH_STRICT_MSGPACK` | Set to `true`. Restricts what the checkpointer will deserialize |

## API

| Endpoint | Who | What |
|---|---|---|
| `GET /health` | anyone | Liveness check |
| `POST /login` | anyone | Email and password → token (valid for one hour) |
| `POST /chat` | customer (Bearer token) | Send a question. Returns `answer`, `thread_id`, `waiting_for_approval` |
| `GET /reviews` | reviewer (`X-Reviewer-Key`) | Requests waiting for a decision |
| `POST /reviews/{id}/decision` | reviewer | `{"approved": true/false}`. Resumes the paused conversation |

## Local development (without Docker for the app)

```bash
python -m venv .venv
.venv\Scripts\activate                   # Windows (use "source .venv/bin/activate" on Linux/macOS)
pip install -e ".[dev]"

docker compose up -d db                  # only the database
alembic upgrade head                     # our tables
python scripts/setup_checkpointer.py     # LangGraph's tables (created by LangGraph, not by Alembic)

uvicorn third_agent.api.app:app --reload
```

## Tests and evaluation

```bash
pytest                                   # fast, free, no model and no database needed
python evals/run_eval.py                 # intent classification and retrieval (calls the model)
python evals/run_agent_eval.py           # end-to-end agent cases, including security cases (calls the model)
```

- **`pytest`**: 43 tests pass and 1 is an expected failure that documents a known limit of the prompt-injection guard. The API tests replace the agent, the database, and the review queue with fakes, so they check the API logic (who can see what, validation, one-time decisions), not the real integration.
- **Intent classification**: 16 of 16 on 16 hand-written Persian questions. The classifier prompt was tuned after seeing early mistakes, so 5 of those questions were written afterward to check it was not memorizing.
- **Retrieval**: the right chunk is in the top 3 for 10 of 10 questions. This is a weak result: there are only 8 chunks from 2 documents, so a random top 3 would already hit 37% of the time.
- **Agent evaluation**: the cases check required and forbidden words in the answers. The model is not deterministic, so results vary between runs and no single number is published here.

## Project layout

```
src/third_agent/
├── agent/       tool definitions and the hand-written agent loop
├── api/         FastAPI app
├── database/    connection, queries, seed data
├── graph/       LangGraph agent graph (agent_graph.py) and the earlier workflow (support_graph.py)
├── mcp/         MCP server (order lookup) and client
├── rag/         chunking, embeddings, ingestion, retrieval
├── auth.py      password hashing (scrypt) and JWT tokens
├── llm.py       calls to the chat model
├── schemas.py   Pydantic models
└── security.py  prompt-injection guard
alembic/         database migrations
docs/knowledge/  shop policy documents used by RAG
evals/           evaluation scripts
scripts/         one-off helper scripts
tests/           pytest tests
```

## Known limitations

- **The prompt-injection guard only knows fixed phrases.** A rephrased attack passes it (one test documents this). Safety does not depend on the guard: identity comes from the token and the only writing tool needs human approval. A system prompt leak is still possible and was seen once with an early version.
- **Small models make mistakes.** The default chat model sometimes invents closing sentences or a status that is not in the data. Prompts reduce this but do not guarantee it, and there is no automatic answer-versus-source check.
- **No rate limiting.** Login attempts and chat requests are not limited.
- **Simple reviewer access.** One shared key, no reviewer identity or audit log.
- **Tokens last one hour and cannot be revoked.** There is no refresh flow and no registration or password reset.
- **No HTTPS.** Run it behind a reverse proxy before exposing it anywhere.
- **Small evaluation sets and tiny document collection.** The numbers above say little about real traffic.
- **Real database behavior is not covered by pytest.** The atomic decision query and the checkpointer are checked only by manual runs.
- **Sample data only.** The shop, customers, and policy documents are made up.
